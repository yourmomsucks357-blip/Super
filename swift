import Foundation

enum AttackVector: String, CaseIterable {
    case credentialStuffing = "credential_stuffing"
    case bruteForce = "brute_force"
    case phishing = "phishing"
    case apiAbuse = "api_abuse"
    case sessionHijacking = "session_hijacking"
    case twoFABypass = "2fa_bypass"

    func execute(target: String, data: [String: Any]) {
        switch self {
        case .credentialStuffing:
            CredentialStuffing().attack(target: target, data: data)
        case .bruteForce:
            BruteForce().attack(target: target, data: data)
        case .phishing:
            Phishing().attack(target: target, data: data)
        case .apiAbuse:
            APIAbuse().attack(target: target, data: data)
        case .sessionHijacking:
            SessionHijacking().attack(target: target, data: data)
        case .twoFABypass:
            TwoFABypass().attack(target: target, data: data)
        }
    }
}
