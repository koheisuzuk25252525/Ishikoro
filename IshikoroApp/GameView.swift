import SwiftUI
import WebKit
import UIKit

struct GameView: UIViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.allowsInlineMediaPlayback = true
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.scrollView.bounces = false
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 0.62, green: 0.80, blue: 0.95, alpha: 1)
        if let url = Bundle.main.url(forResource: "ishikoro", withExtension: "html"),
           let data = try? Data(contentsOf: url) {
            // Declare the byte encoding to WebKit itself as well as in HTML.
            // Keep the bundled file URL as the base for the existing save origin.
            webView.load(
                data,
                mimeType: "text/html",
                characterEncodingName: "utf-8",
                baseURL: url
            )
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
