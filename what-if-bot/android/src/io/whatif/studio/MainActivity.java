package io.whatif.studio;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;

/**
 * Single-activity WebView shell for $IF Studio.
 *
 * The UI is the same HTML that runs in a desktop browser, loaded from
 * assets/ so it works with no server. Written in Java 7 style (no lambdas)
 * because the build pipeline dexes with legacy dx, which does not desugar.
 */
public class MainActivity extends Activity {

    private static final String PAGE = "file:///android_asset/studio.html";
    private WebView web;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);

        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        // localStorage — this is where the A/B training data lives.
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        // Images come from an https API while the page origin is file://.
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);

        web.setBackgroundColor(0xFF070A07);
        web.addJavascriptInterface(new Bridge(), "IFBridge");

        // Keep in-app navigation inside the WebView; send real links out to
        // the browser so a stray tap can't strand the user in a dead page.
        // Only the String overload is implemented: on API 24+ the framework's
        // WebResourceRequest version delegates to it, so this covers every
        // supported release while still compiling against the API 23 jar.
        web.setWebViewClient(new WebViewClient() {
            @SuppressWarnings("deprecation")
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, String url) {
                return openExternally(Uri.parse(url));
            }
        });

        web.setWebChromeClient(new WebChromeClient());

        if (state != null) {
            web.restoreState(state);
        } else {
            web.loadUrl(PAGE);
        }
    }

    private boolean openExternally(Uri uri) {
        String scheme = uri.getScheme();
        if (scheme == null || scheme.equals("file")) {
            return false;
        }
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception e) {
            toast("No app can open that link");
        }
        return true;
    }

    /** Exposed to the page as window.IFBridge. */
    private class Bridge {
        /**
         * Writes exported training data to the app's Downloads folder.
         * Uses the app-specific external dir, so no storage permission and
         * no scoped-storage headaches.
         */
        @JavascriptInterface
        public String saveText(String name, String content) {
            OutputStreamWriter w = null;
            try {
                File dir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
                if (dir == null) {
                    dir = getFilesDir();
                }
                if (!dir.exists()) {
                    dir.mkdirs();
                }
                File out = new File(dir, name);
                w = new OutputStreamWriter(new FileOutputStream(out), "UTF-8");
                w.write(content);
                w.close();
                w = null;
                final String path = out.getAbsolutePath();
                runOnUiThread(new Runnable() {
                    public void run() {
                        toast("Saved to " + path);
                    }
                });
                return path;
            } catch (Exception e) {
                runOnUiThread(new Runnable() {
                    public void run() {
                        toast("Save failed");
                    }
                });
                return "";
            } finally {
                if (w != null) {
                    try { w.close(); } catch (Exception ignored) { }
                }
            }
        }

        /** Opens a generated image full size in the browser. */
        @JavascriptInterface
        public void openUrl(final String url) {
            runOnUiThread(new Runnable() {
                public void run() {
                    openExternally(Uri.parse(url));
                }
            });
        }
    }

    private void toast(String msg) {
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show();
    }

    @Override
    public boolean onKeyDown(int code, KeyEvent e) {
        // Back button walks the in-page history (tab switches) before exiting.
        if (code == KeyEvent.KEYCODE_BACK && web != null && web.canGoBack()) {
            web.goBack();
            return true;
        }
        return super.onKeyDown(code, e);
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    protected void onPause() {
        super.onPause();
        web.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        web.onResume();
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}
