import SwiftUI
import WebKit
import UIKit

struct GameView: UIViewRepresentable {
    @Environment(\.scenePhase) private var scenePhase

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.allowsInlineMediaPlayback = true
        let webView = WKWebView(frame: .zero, configuration: configuration)
        context.coordinator.isAppActive = scenePhase == .active
        webView.navigationDelegate = context.coordinator
        webView.scrollView.bounces = false
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 0.62, green: 0.80, blue: 0.95, alpha: 1)
        #if DEBUG
        let resource = ProcessInfo.processInfo.arguments.contains("--adventure-prototype")
            ? "adventure" : "ishikoro"
        #else
        let resource = "ishikoro"
        #endif
        if let url = Bundle.main.url(forResource: resource, withExtension: "html"),
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

    func updateUIView(_ uiView: WKWebView, context: Context) {
        let isActive = scenePhase == .active
        if context.coordinator.isAppActive != isActive {
            context.coordinator.isAppActive = isActive
            context.coordinator.sendAppState(to: uiView)
        }
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        var isAppActive = true

        func sendAppState(to webView: WKWebView) {
            let event = isAppActive ? "ishikoro:active" : "ishikoro:background"
            webView.evaluateJavaScript("window.dispatchEvent(new Event('\(event)'))", completionHandler: nil)
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            sendAppState(to: webView)
        }

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
