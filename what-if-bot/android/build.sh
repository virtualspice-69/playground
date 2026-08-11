#!/usr/bin/env bash
# Builds $IF Studio.apk without Android Studio or Gradle.
#
# Toolchain (all installable on Debian/Ubuntu):
#   apt-get install -y aapt android-sdk-build-tools android-sdk-platform-23 default-jdk
#   plus dx from Maven Central (auto-downloaded below)
#
# Usage: ./build.sh
# Output: build/IF-Studio.apk

set -euo pipefail
cd "$(dirname "$0")"

PKG_DIR=io/whatif/studio
ANDROID_JAR=${ANDROID_JAR:-/usr/lib/android-sdk/platforms/android-23/android.jar}
DX_JAR=${DX_JAR:-/tmp/dxtool/dalvik-dx-16.0.1.jar}
DX_URL=https://repo1.maven.org/maven2/com/jakewharton/android/repackaged/dalvik-dx/16.0.1/dalvik-dx-16.0.1.jar
OUT=build
APK=$OUT/IF-Studio.apk
KEYSTORE=$OUT/signing.keystore
STOREPASS=ifstudio

command -v aapt      >/dev/null || { echo "missing aapt (apt-get install aapt)"; exit 1; }
command -v zipalign  >/dev/null || { echo "missing zipalign (apt-get install android-sdk-build-tools)"; exit 1; }
command -v apksigner >/dev/null || { echo "missing apksigner (apt-get install android-sdk-build-tools)"; exit 1; }
[ -f "$ANDROID_JAR" ] || { echo "missing android.jar at $ANDROID_JAR (apt-get install android-sdk-platform-23)"; exit 1; }

if [ ! -f "$DX_JAR" ]; then
  echo "==> fetching dx"
  mkdir -p "$(dirname "$DX_JAR")"
  curl -sSfL "$DX_URL" -o "$DX_JAR"
fi

rm -rf "$OUT"
mkdir -p "$OUT/classes" "$OUT/gen" "$OUT/apk"

echo "==> staging web assets"
mkdir -p assets
cp ../studio/if-studio.html assets/studio.html

echo "==> generating R.java"
aapt package -f -m \
  -J "$OUT/gen" \
  -M AndroidManifest.xml \
  -S res \
  -I "$ANDROID_JAR"

echo "==> compiling java"
# --release 8: legacy dx cannot read class files newer than Java 8.
javac -nowarn --release 8 \
  -classpath "$ANDROID_JAR" \
  -d "$OUT/classes" \
  "$OUT/gen/$PKG_DIR/R.java" \
  "src/$PKG_DIR/MainActivity.java"

echo "==> dexing"
java -cp "$DX_JAR" com.android.dx.command.Main \
  --dex --min-sdk-version=23 \
  --output="$OUT/apk/classes.dex" \
  "$OUT/classes"

echo "==> packaging resources"
aapt package -f \
  -M AndroidManifest.xml \
  -S res \
  -A assets \
  -I "$ANDROID_JAR" \
  -F "$OUT/unsigned.apk"

echo "==> adding dex"
( cd "$OUT/apk" && aapt add -f "../unsigned.apk" classes.dex >/dev/null )

echo "==> signing"
if [ ! -f "$KEYSTORE" ]; then
  keytool -genkeypair -v \
    -keystore "$KEYSTORE" \
    -alias ifstudio \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass "$STOREPASS" -keypass "$STOREPASS" \
    -dname "CN=What IF Studio, OU=Community, O=What IF, L=, ST=, C=US" 2>/dev/null
fi

zipalign -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
apksigner sign \
  --ks "$KEYSTORE" \
  --ks-pass "pass:$STOREPASS" \
  --key-pass "pass:$STOREPASS" \
  --out "$APK" \
  "$OUT/aligned.apk"

rm -f "$OUT/unsigned.apk" "$OUT/aligned.apk" "$APK.idsig"
rm -rf "$OUT/classes" "$OUT/gen" "$OUT/apk"

echo
apksigner verify --print-certs "$APK" | head -3
echo
ls -lh "$APK"
echo "==> done: $APK"
