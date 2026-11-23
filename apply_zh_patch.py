# -*- coding: utf-8 -*-
"""ACNHMobileSpawner 简体中文汉化补丁。
在 Unity 构建之前运行，对工程源码做原地修改：
 1) MainScene.unity 中的静态 UI 文案 -> 中文
 2) C# 脚本中的运行时字符串 -> 中文
 3) 注入中文字体（NotoSansCJKsc-Regular.otf），把所有 Text 的字体指向它
 4) 默认语言改为简体中文 zhs（GameLanguage.DefaultLanguage / UI_Settings 默认值）

用法： python apply_zh_patch.py <Unity工程根目录>
例如： python apply_zh_patch.py ACNHMS_src/ACNHMS_Source
"""
import sys, os, re, json, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from zh_map import SCENE_MAP, SCRIPT_MAP
try:
    from zh_map import SCRIPT_MAP_BY_FILE
except ImportError:
    # 兼容旧版 zh_map.py（没有按文件定向映射）：降级为空，不影响主流程
    SCRIPT_MAP_BY_FILE = {}

FONT_FILE = "NotoSansCJKsc-Regular.otf"
FONT_GUID = "a1b2c3d4e5f60718293a4b5c6d7e8f90"  # 固定 32 位 guid
BUILTIN_ARIAL = "{fileID: 10102, guid: 0000000000000000e000000000000000, type: 0}"
# 项目自带的等宽字体 RobotoMono，被 IP/端口/十六进制数值等输入框使用。
# 它在 iOS 上不渲染，必须一并替换成中文字体，否则这些输入框显示空白。
ROBOTO_MONO = "{fileID: 12800000, guid: c4b417931926fac47923d5f75f316c95, type: 3}"
CJK_FONT_REF = "{fileID: 12800000, guid: %s, type: 3}" % FONT_GUID


def unescape(v):
    v = v.replace('\\"', '"').replace('\\\\', '\\')
    v = v.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
    def u(m):
        try:
            return chr(int(m.group(1), 16))
        except Exception:
            return m.group(0)
    v = re.sub(r'\\u([0-9a-fA-F]{4})', u, v)
    v = re.sub(r'\\x([0-9a-fA-F]{2})', u, v)
    return v


def parse_scalar(raw):
    raw = raw.strip()
    if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
        return True, unescape(raw[1:-1])
    if len(raw) >= 2 and raw.startswith("'") and raw.endswith("'"):
        return True, raw[1:-1].replace("''", "'")
    return False, raw


def escape_yaml_double(text):
    # Unity/YAML 双引号标量转义
    text = text.replace('\\', '\\\\').replace('"', '\\"')
    text = text.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')
    return '"' + text + '"'


def patch_scene(path):
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        s = f.read()
    replaced = 0

    def do_text(m):
        nonlocal replaced
        prefix, raw = m.group(1), m.group(2)
        quoted, plain = parse_scalar(raw)
        zh = SCENE_MAP.get(plain)
        if zh is None or zh == plain:
            return m.group(0)
        replaced += 1
        return prefix + escape_yaml_double(zh)

    s = re.sub(r'(m_Text:\s*)(.*)', do_text, s)

    # 字体：把内置 Arial 和 RobotoMono(输入框用) 都替换为中文字体引用
    font_hits = s.count(BUILTIN_ARIAL)
    s = s.replace(BUILTIN_ARIAL, CJK_FONT_REF)
    font_hits += s.count(ROBOTO_MONO)
    s = s.replace(ROBOTO_MONO, CJK_FONT_REF)

    # 中文字体 Noto Sans CJK SC 行高约 1.45em，比原来的 Arial(约1.0em)高很多。
    # 原本按英文高度设计的输入框标签(如 Mon:/AM:，框高约44px < 中文字行高52px)，
    # 换成中文字体后会被 VerticalOverflow=Truncate 整行裁掉 → 文字完全不显示。
    # 对所有含中文的 Text 组件，把水平/垂直溢出都改为 Overflow，避免被裁剪。
    overflow_fixed = 0
    blocks = re.split(r'(?=--- !u!)', s)
    fixed_blocks = []
    for blk in blocks:
        tm = re.search(r'm_Text:\s*(.*)', blk)
        if tm and re.search(r'[\u4e00-\u9fff]', tm.group(1)):
            new_blk = blk.replace('m_HorizontalOverflow: 0', 'm_HorizontalOverflow: 1')
            new_blk = new_blk.replace('m_VerticalOverflow: 0', 'm_VerticalOverflow: 1')
            if new_blk != blk:
                overflow_fixed += 1
            fixed_blocks.append(new_blk)
        else:
            fixed_blocks.append(blk)
    s = ''.join(fixed_blocks)

    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    return replaced, font_hits


def patch_scripts(root):
    changed, hits = [], 0
    for dirpath, _, files in os.walk(os.path.join(root, 'Assets', 'Scripts')):
        for name in files:
            if not name.endswith('.cs'):
                continue
            p = os.path.join(dirpath, name)
            with open(p, encoding='utf-8-sig', errors='replace') as f:
                src = f.read()
            orig = src
            # 通用映射 + 仅对本文件生效的定向映射
            local_map = dict(SCRIPT_MAP)
            local_map.update(SCRIPT_MAP_BY_FILE.get(name, {}))
            def repl(m):
                nonlocal hits
                plain = m.group(1).replace('\\"', '"').replace('\\n', '\n')
                zh = local_map.get(plain)
                if zh is None:
                    return m.group(0)
                hits += 1
                return '"' + zh.replace('"', '\\"').replace('\n', '\\n') + '"'
            src = re.sub(r'"((?:[^"\\]|\\.)*)"', repl, src)
            if src != orig:
                with open(p, 'w', encoding='utf-8', newline='') as f:
                    f.write(src)
                changed.append(name)
    return changed, hits


def patch_default_language(root):
    """默认语言改为 zhs（索引 7）"""
    notes = []
    # GameLanguage.cs
    gl = os.path.join(root, 'Assets', 'Scripts', 'Core', 'Strings', 'GameLanguage.cs')
    if os.path.exists(gl):
        s = open(gl, encoding='utf-8-sig', errors='replace').read()
        s2 = s.replace('public const string DefaultLanguage = "en";',
                       'public const string DefaultLanguage = "zhs";')
        if s2 != s:
            open(gl, 'w', encoding='utf-8', newline='').write(s2)
            notes.append('GameLanguage.DefaultLanguage -> zhs')
    # UI_Settings.cs 默认语言索引：GetLanguage(int defLang = 0) -> 7
    us = os.path.join(root, 'Assets', 'Scripts', 'ACNHMS', 'UI_Settings.cs')
    if os.path.exists(us):
        s = open(us, encoding='utf-8-sig', errors='replace').read()
        s2 = re.sub(r'GetLanguage\(int defLang = 0\)', 'GetLanguage(int defLang = 7)', s)
        if s2 != s:
            open(us, 'w', encoding='utf-8', newline='').write(s2)
            notes.append('UI_Settings.GetLanguage default -> 7(zhs)')
    return notes


def install_font(root):
    """把中文字体放进 Assets/Fonts 并生成 .meta"""
    fonts_dir = os.path.join(root, 'Assets', 'Fonts')
    os.makedirs(fonts_dir, exist_ok=True)
    src = os.path.join(HERE, FONT_FILE)
    dst = os.path.join(fonts_dir, FONT_FILE)
    if os.path.exists(src):
        shutil.copyfile(src, dst)
    meta = os.path.join(fonts_dir, FONT_FILE + '.meta')
    # 若 meta 不存在，或是旧版本（缺 externalObjects 字段），都重写为完整模板
    need_meta = True
    if os.path.exists(meta):
        existing = open(meta, encoding='utf-8', errors='replace').read()
        guid_line = [l for l in existing.splitlines() if l.strip().startswith('guid:')]
        valid_guid = bool(guid_line) and FONT_GUID in guid_line[0] and '%s' not in existing
        if 'externalObjects' in existing and 'assetBundleVariant' in existing and valid_guid:
            need_meta = False
    if need_meta:
        with open(meta, 'w', encoding='utf-8', newline='') as f:
            f.write((
                "fileFormatVersion: 2\n"
                "guid: %s\n"
                "TrueTypeFontImporter:\n"
                "  externalObjects: {}\n"
                "  serializedVersion: 4\n"
                "  fontSize: 16\n"
                "  forceTextureCase: -2\n"
                "  characterSpacing: 0\n"
                "  characterPadding: 1\n"
                "  includeFontData: 1\n"
                "  fontName: Noto Sans CJK SC\n"
                "  fontNames:\n"
                "  - Noto Sans CJK SC\n"
                "  fallbackFontReferences: []\n"
                "  customCharacters: \n"
                "  fontRenderingMode: 0\n"
                "  ascentCalculationMode: 1\n"
                "  useLegacyBoundsCalculation: 0\n"
                "  shouldRoundAdvanceValue: 1\n"
                "  userData: \n"
                "  assetBundleName: \n"
                "  assetBundleVariant: \n"
            ) % FONT_GUID)
    return os.path.exists(dst)


def fix_compile_errors(root):
    """修复原工程自身在较新 NHSE.Core 库下的两个编译错误（与汉化无关）。
    ItemInfo.cs 的堆叠数量字典引用了 ItemKind 枚举中不存在的两个成员，
    导致 Unity 6 编译时报 CS0103。注释掉这两行即可（对应物品类型在当前库中不存在）。
    """
    p = os.path.join(root, 'Assets', 'Scripts', 'Core', 'Structures', 'Item', 'ItemInfo.cs')
    if not os.path.exists(p):
        return []
    s = open(p, encoding='utf-8-sig', errors='replace').read()
    orig = s
    fixed = []
    for kind in ('Kind_SubToolEat', 'Kind_XmasDeco'):
        # 精确匹配字典行：{Kind_xxx, 数字},  —— 注意不能误伤 Kind_SubToolEatDrop / Remakeable
        pattern = r'(\s*)\{' + re.escape(kind) + r',\s*[0-9]+\},'
        def repl(m):
            fixed.append(kind)
            return m.group(1) + '// [zh-patch] disabled: undefined enum member ' + kind
        s = re.sub(pattern, repl, s)
    if s != orig:
        open(p, 'w', encoding='utf-8', newline='').write(s)
    return fixed


def main():
    if len(sys.argv) < 2:
        print("usage: python apply_zh_patch.py <UnityProjectRoot>")
        sys.exit(1)
    root = sys.argv[1]
    scene = os.path.join(root, 'Assets', 'Scenes', 'MainScene.unity')
    stats = {}
    if os.path.exists(scene):
        n, f = patch_scene(scene)
        stats['scene_texts'] = n
        stats['font_refs'] = f
    else:
        stats['scene_error'] = 'MainScene.unity not found'
    changed, hits = patch_scripts(root)
    stats['script_files'] = changed
    stats['script_hits'] = hits
    stats['language'] = patch_default_language(root)
    stats['font_installed'] = install_font(root)
    stats['compile_fixes'] = fix_compile_errors(root)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
