import SwiftUI
import WebKit
import UIKit

struct GameView: UIViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.allowsInlineMediaPlayback = true
        // The supplied HTML has no viewport declaration. Add one without
        // changing the shared game source or its save/edition formats.
        configuration.userContentController.addUserScript(WKUserScript(
            source: """
            if (!document.querySelector('meta[name="viewport"]')) {
                const viewport = document.createElement('meta');
                viewport.name = 'viewport';
                viewport.content = 'width=device-width, initial-scale=1';
                document.head.appendChild(viewport);
            }
            """,
            injectionTime: .atDocumentEnd,
            forMainFrameOnly: true
        ))
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.scrollView.bounces = false
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 0.62, green: 0.80, blue: 0.95, alpha: 1)
        if let url = Bundle.main.url(forResource: "ishikoro", withExtension: "html") {
            webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        }
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKNavigationDelegate {
        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            // Open shop links in the system browser, including target=_blank.
            if navigationAction.navigationType == .linkActivated,
               let url = navigationAction.request.url,
               ["https", "http"].contains(url.scheme?.lowercased() ?? "") {
                UIApplication.shared.open(url)
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }
    }
}
