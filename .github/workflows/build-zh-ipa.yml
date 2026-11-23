name: 构建中文 IPA (ACNHMobileSpawner) v3

on:
  workflow_dispatch:

jobs:
  build-ipa:
    name: 汉化并构建中文 IPA
    runs-on: macos-15-intel
    timeout-minutes: 180
    steps:
      - name: 检出代码
        uses: actions/checkout@v4
        with:
          lfs: true

      - name: 安装 Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 下载中文字体
        run: |
          URL="https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
          curl -fL --retry 4 --retry-delay 3 -o NotoSansCJKsc-Regular.otf "$URL" \
            || curl -fL --retry 4 -o NotoSansCJKsc-Regular.otf \
              "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
          test -s NotoSansCJKsc-Regular.otf

      - name: 应用简体中文补丁
        run: |
          export PYTHONDONTWRITEBYTECODE=1
          python apply_zh_patch.py ACNHMS_Source

      - name: 提交汉化改动（保持分支干净）
        run: |
          git config user.name "CI Builder"
          git config user.email "ci@builder.local"
          git add -A
          git -c commit.gpgsign=false commit -m "Apply zh-CN localization patch" || echo "nothing to commit"

      # 用 Unity 官方 CLI 安装编辑器和 iOS 模块（已验证在 runner 上工作正常）
      - name: 安装 Unity 6000.3.4f1 + iOS 模块
        run: |
          curl -fsSL https://unity.com/install.sh | bash
          # macOS 上该脚本默认装到 ~/.unity/bin/unity（home 模式），Linux 才是 ~/.local/bin。
          # 逐一探测，找到可用的 unity CLI 绝对路径，避免依赖 shell 重启后才生效的 PATH。
          UNITY_CLI=""
          for c in "$HOME/.unity/bin/unity" "$HOME/.local/bin/unity" "$(command -v unity 2>/dev/null)"; do
            if [ -n "$c" ] && [ -x "$c" ]; then UNITY_CLI="$c"; break; fi
          done
          if [ -z "$UNITY_CLI" ]; then
            UNITY_CLI=$(find "$HOME" -maxdepth 5 -type f -name unity -perm -u+x 2>/dev/null | head -n 1)
          fi
          echo "unity CLI: $UNITY_CLI"
          test -n "$UNITY_CLI" && test -x "$UNITY_CLI"
          "$UNITY_CLI" install 6000.3.4f1 -m ios -a x86_64 --cm --accept-eula --yes
          "$UNITY_CLI" editors -i
          test -x "/Applications/Unity/Hub/Editor/6000.3.4f1/Unity.app/Contents/MacOS/Unity"

      # 写入自定义 build script：从激活的场景构建 iOS Xcode 工程，输出到 build/iOS
      - name: 写入构建脚本
        run: |
          mkdir -p ACNHMS_Source/Assets/Editor
          cat > ACNHMS_Source/Assets/Editor/CIBuild.cs <<'CS'
          using System;
          using System.Linq;
          using UnityEditor;
          using UnityEditor.Build.Reporting;
          using UnityEngine;

          public static class CIBuild
          {
              public static void BuildIOS()
              {
                  // ---- 字体自检：确认中文字体被正确导入 ----
                  var fontPath = "Assets/Fonts/NotoSansCJKsc-Regular.otf";
                  var f = AssetDatabase.LoadAssetAtPath<Font>(fontPath);
                  Debug.Log("[ZH-FONT] exists=" + System.IO.File.Exists(fontPath) + " loaded=" + (f != null));
                  if (f != null)
                  {
                      Debug.Log("[ZH-FONT] name=" + f.name + " dynamic=" + f.dynamic +
                                " fontSize=" + f.fontSize + " textureCount=" + f.fontNames.Length);
                      Debug.Log("[ZH-FONT] fontNames=" + string.Join("|", f.fontNames));
                  }
                  else
                  {
                      Debug.LogError("[ZH-FONT] FAILED to load Chinese font - text will be blank!");
                  }
                  var scenes = EditorBuildSettings.scenes
                      .Where(s => s.enabled)
                      .Select(s => s.path)
                      .ToArray();
                  if (scenes.Length == 0)
                  {
                      Debug.LogError("No enabled scenes in Build Settings!");
                      EditorApplication.Exit(1);
                      return;
                  }
                  Debug.Log("Building scenes: " + string.Join(", ", scenes));
                  // 用环境变量传入的绝对路径，确保 Xcode 工程输出到仓库根目录的 build/iOS
                  var outDir = System.Environment.GetEnvironmentVariable("CI_BUILD_OUTPUT");
                  if (string.IsNullOrEmpty(outDir))
                      outDir = "build/iOS";
                  Debug.Log("Build output: " + outDir);
                  var opts = new BuildPlayerOptions
                  {
                      scenes = scenes,
                      locationPathName = outDir,
                      target = BuildTarget.iOS,
                      options = BuildOptions.None
                  };
                  var report = BuildPipeline.BuildPlayer(opts);
                  Debug.Log("Build result: " + report.summary.result);
                  if (report.summary.result != BuildResult.Succeeded)
                      EditorApplication.Exit(1);
              }
          }
          CS
          git add -f ACNHMS_Source/Assets/Editor/CIBuild.cs
          git -c commit.gpgsign=false commit -m "Add CI build script" || echo "nothing to commit"

      # 显式激活个人 NUL 许可证（GameCI v6 已验证这套参数对个人账号有效）
      - name: 激活 Unity 个人许可证
        run: |
          LC="/Applications/Unity/Hub/Editor/6000.3.4f1/Unity.app/Contents/Helpers/UnityLicensingClient.app/Contents/MacOS/Unity.Licensing.Client"
          ls -l "$LC"
          "$LC" --activate-all --include-personal --username "$UNITY_EMAIL" --password "$UNITY_PASSWORD"
          echo "---- license activated ----"
        env:
          UNITY_EMAIL: ${{ secrets.UNITY_EMAIL }}
          UNITY_PASSWORD: ${{ secrets.UNITY_PASSWORD }}

      # 直接用 Unity 可执行文件构建，日志写入文件（不像 GameCI 那样删掉）
      - name: Unity 构建 iOS Xcode 工程
        timeout-minutes: 120
        run: |
          UNITY="/Applications/Unity/Hub/Editor/6000.3.4f1/Unity.app/Contents/MacOS/Unity"
          "$UNITY" \
            -batchmode \
            -nographics \
            -quit \
            -logFile "$PWD/unity-build.log" \
            -projectPath "$PWD/ACNHMS_Source" \
            -buildTarget iOS \
            -username "$UNITY_EMAIL" \
            -password "$UNITY_PASSWORD" \
            -executeMethod CIBuild.BuildIOS
          STATUS=$?
          echo "Unity exit code: $STATUS"
          echo "========== UNITY BUILD LOG (errors) =========="
          grep -iE "error|exception|failed|abort|Build result|Building scenes" unity-build.log | tail -100 || true
          # 把所有可能的编译错误做成 annotation，直接显示在 Actions 页面顶部（也可从 API 读取）
          grep -iE "error CS[0-9]+|\.cs\([0-9]+|Scripts have compiler errors|error:|Compilation failed|error [A-Z]+[0-9]+" \
            unity-build.log 2>/dev/null | sort -u | head -25 | while IFS= read -r line; do
            echo "::error::${line:0:500}"
          done || true
          echo "========== UNITY BUILD LOG (tail) =========="
          tail -80 unity-build.log || true
          echo "========== BUILD OUTPUT =========="
          find build -maxdepth 5 \( -name "*.xcodeproj" -o -name "*.xcworkspace" \) -print 2>/dev/null || true
          echo "---- also check project-local build dir ----"
          find ACNHMS_Source/build -maxdepth 5 \( -name "*.xcodeproj" -o -name "*.xcworkspace" \) -print 2>/dev/null || true
          exit $STATUS
        env:
          UNITY_EMAIL: ${{ secrets.UNITY_EMAIL }}
          UNITY_PASSWORD: ${{ secrets.UNITY_PASSWORD }}
          CI_BUILD_OUTPUT: ${{ github.workspace }}/build/iOS

      - name: 上传构建日志
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: unity-build-log
          path: unity-build.log
          if-no-files-found: warn
          retention-days: 7

      - name: 选择最新 Xcode
        run: sudo xcode-select -s /Applications/Xcode.app/Contents/Developer

      - name: 归档 (无签名)
        run: |
          # 在两个可能位置查找 Unity 导出的 Xcode 工程
          WS=$(find build ACNHMS_Source/build -maxdepth 6 -name "*.xcworkspace" 2>/dev/null | head -n 1)
          PROJ=$(find build ACNHMS_Source/build -maxdepth 6 -name "*.xcodeproj" 2>/dev/null | head -n 1)
          echo "workspace=$WS project=$PROJ"
          test -n "$WS$PROJ" || { echo "::error::未找到 Xcode 工程，检查 Unity 构建日志"; exit 1; }
          if [ -n "$WS" ]; then
            xcodebuild -workspace "$WS" -scheme Unity-iPhone -configuration Release \
              -archivePath "$PWD/build/Unity-iPhone.xcarchive" \
              CODE_SIGNING_ALLOWED=NO clean archive
          else
            xcodebuild -project "$PROJ" -scheme Unity-iPhone -configuration Release \
              -archivePath "$PWD/build/Unity-iPhone.xcarchive" \
              CODE_SIGNING_ALLOWED=NO clean archive
          fi

      - name: 导出未签名 IPA
        run: |
          mkdir -p Payload ipa-out
          APP=$(find build/Unity-iPhone.xcarchive/Products -maxdepth 4 -name "*.app" | head -n 1)
          echo "APP=$APP"
          test -n "$APP"
          cp -R "$APP" Payload/
          rm -rf Payload/*.app/Watch Payload/*.app/_CodeSignature Payload/*.app/embedded.mobileprovision
          zip -qry ipa-out/ACNHMobileSpawner-zh-CN.ipa Payload
          ls -lh ipa-out/

      - name: 上传 IPA
        uses: actions/upload-artifact@v4
        with:
          name: ACNHMobileSpawner-zh-CN-ipa
          path: ipa-out/*.ipa
          retention-days: 30
