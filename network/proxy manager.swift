import Foundation

class ProxyManager {
    private var proxies: [String] = []

    init(proxyFilePath: String = "Resources/Configs/proxies.txt") {
        loadProxies(from: proxyFilePath)
    }

    private func loadProxies(from filePath: String) {
        do {
            let contents = try String(contentsOfFile: filePath, encoding: .utf8)
            proxies = contents.components(separatedBy: .newlines).filter { !$0.isEmpty }
        } catch {
            print("Error loading proxies: \(error)")
        }
    }

    func getRandomProxy() -> String? {
        return proxies.randomElement()
    }

    func rotateProxy() -> String {
        // Rotate to the next proxy in the list
        if proxies.isEmpty { return "" }
        let currentProxy = proxies.removeFirst()
        proxies.append(currentProxy)
        return currentProxy
    }
}
