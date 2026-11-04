import { ApiError } from "@/lib/api/client";
export function authMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if(error.code==="draft_cleanup_failed")return "You are signed out, but local Reading data could not be removed. Clear this site’s browser data before sharing this device.";
    if (error.code === "different_account") return "Log out of the current account before registering another email.";
    if (error.code === "auth_not_configured") return "Account access isn’t configured yet. Please contact the Alua site owner.";
    if (error.code === "api_not_configured") return "The Alua service isn’t configured yet. Please contact the site owner.";
    if (error.code === "timeout") return "The connection is taking too long. Please try again.";
    if (error.status === 401) return "Your session has expired. Please log in again.";
    if (error.status === 403) return "This account does not have Alua access.";
    if (error.status === 429) return "Too many requests. Please try again later.";
    if (error.code === "registration_disabled") return "Registration is temporarily unavailable. Your Firebase account is preserved; try completing setup later.";
    if (error.status >= 500) return "The Alua service is temporarily unavailable. Please try again.";
    return "Couldn’t connect to Alua. Check your connection and try again.";
  }
  const code = error && typeof error === "object" && "code" in error ? error.code : "";
  switch (code) {
    case "auth/popup-closed-by-user": case "auth/cancelled-popup-request": return "Google sign-in was cancelled. You can try again whenever you’re ready.";
    case "auth/popup-blocked": return "Your browser blocked the Google window. Allow popups for this website and try again.";
    case "auth/provider-already-linked": return "Google is already connected to this account. Choose Continue to return to your practice.";
    case "auth/credential-already-in-use": return "This Google account is connected to another identity. Use its existing sign-in method; your accounts have not been merged.";
    case "auth/account-exists-with-different-credential": return "This email uses another sign-in method. Log in with your existing method to keep your Alua account and progress.";
    case "auth/invalid-email": return "Enter a valid email address.";
    case "auth/invalid-credential": case "auth/wrong-password": case "auth/user-not-found":
      return "The email or password is incorrect. Check your details or reset your password.";
    case "auth/email-already-in-use": return "This email is already registered. Log in or reset your password to continue.";
    case "auth/weak-password": case "auth/password-does-not-meet-requirements": return "Choose a stronger password that meets the account password policy.";
    case "auth/network-request-failed": return "Couldn’t connect. Check your internet connection and try again.";
    case "auth/too-many-requests": return "Too many attempts. Please try again later.";
    case "auth/user-disabled": return "This account has been disabled. Please contact the Alua site owner.";
    case "auth/operation-not-allowed": return "Email and password access is currently unavailable. Please contact the site owner.";
    case "auth/invalid-api-key": case "auth/app-not-authorized": case "auth/unauthorized-domain":
      return "Account access isn’t configured for this website. Please contact the site owner.";
    case "auth/web-storage-unsupported": return "Allow website storage in your browser to keep your Alua session.";
    default: return "Couldn’t complete this request. Please try again.";
  }
}
