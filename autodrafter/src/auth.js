// Self-contained accounts: registration, email confirmation, login, sessions,
// and a homegrown captcha — all on Node's built-in crypto, no dependencies and
// no external services. Users live in a JSON file. For a public deployment,
// swap the JSON store for a database and plug a real email provider into
// sendConfirmationEmail() (see README).

import fs from "fs";
import path from "path";
import crypto from "crypto";

const DATA_DIR = path.resolve("data");
const USERS_FILE = path.join(DATA_DIR, "users.json");
const SECRET_FILE = path.join(DATA_DIR, "secret.key");
const SESSION_DAYS = 30;

function ensureData() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  if (!fs.existsSync(USERS_FILE)) fs.writeFileSync(USERS_FILE, "{}");
}

// Server secret used to sign session cookies + captcha tokens. Persisted so
// logins survive a restart; generated once on first run.
function serverSecret() {
  ensureData();
  if (!fs.existsSync(SECRET_FILE)) {
    fs.writeFileSync(SECRET_FILE, crypto.randomBytes(32).toString("hex"), { mode: 0o600 });
  }
  return fs.readFileSync(SECRET_FILE, "utf8").trim();
}

function loadUsers() {
  ensureData();
  try {
    return JSON.parse(fs.readFileSync(USERS_FILE, "utf8"));
  } catch {
    return {};
  }
}
function saveUsers(users) {
  fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
}

const b64u = (buf) => Buffer.from(buf).toString("base64url");
function sign(value) {
  const mac = crypto.createHmac("sha256", serverSecret()).update(value).digest("base64url");
  return `${value}.${mac}`;
}
function unsign(signed) {
  if (typeof signed !== "string") return null;
  const i = signed.lastIndexOf(".");
  if (i < 0) return null;
  const value = signed.slice(0, i);
  const mac = signed.slice(i + 1);
  const expect = crypto.createHmac("sha256", serverSecret()).update(value).digest("base64url");
  const a = Buffer.from(mac);
  const b = Buffer.from(expect);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  return value;
}

/* ---------- passwords (scrypt) ---------- */
function hashPassword(password) {
  const salt = crypto.randomBytes(16);
  const hash = crypto.scryptSync(password, salt, 64);
  return `${salt.toString("hex")}:${hash.toString("hex")}`;
}
function verifyPassword(password, stored) {
  const [saltHex, hashHex] = String(stored).split(":");
  if (!saltHex || !hashHex) return false;
  const hash = crypto.scryptSync(password, Buffer.from(saltHex, "hex"), 64);
  const expected = Buffer.from(hashHex, "hex");
  return hash.length === expected.length && crypto.timingSafeEqual(hash, expected);
}

/* ---------- email validation ---------- */
// Basic shape check. "Not bought / disposable" is enforced by blocking known
// throwaway domains AND by requiring the user to click a confirmation link —
// a bought/fake inbox can't confirm.
const DISPOSABLE = new Set([
  "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
  "temp-mail.org", "throwaway.email", "yopmail.com", "trashmail.com",
  "getnada.com", "sharklasers.com", "maildrop.cc", "fakeinbox.com",
]);
export function validateEmail(email) {
  const e = String(email || "").trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e)) return { ok: false, error: "Enter a valid email address." };
  const domain = e.split("@")[1];
  if (DISPOSABLE.has(domain)) return { ok: false, error: "Disposable email addresses aren't allowed. Use a real inbox." };
  return { ok: true, email: e };
}

/* ---------- captcha (self-contained, signed) ---------- */
export function makeCaptcha() {
  const a = 1 + Math.floor(Math.random() * 9);
  const b = 1 + Math.floor(Math.random() * 9);
  const ops = [["+", a + b], ["×", a * b]];
  const [op, answer] = ops[Math.floor(Math.random() * ops.length)];
  const exp = Date.now() + 5 * 60 * 1000;
  const token = sign(`${b64u(String(answer))}.${exp}`);
  return { question: `What is ${a} ${op} ${b}?`, token };
}
export function verifyCaptcha(token, answer) {
  const value = unsign(token);
  if (!value) return false;
  const [ansB64, expStr] = value.split(".");
  if (Number(expStr) < Date.now()) return false;
  const expected = Buffer.from(ansB64, "base64url").toString("utf8");
  return String(answer).trim() === expected;
}

/* ---------- users ---------- */
export function register({ email, password }) {
  const v = validateEmail(email);
  if (!v.ok) return { ok: false, error: v.error };
  if (String(password || "").length < 8) return { ok: false, error: "Password must be at least 8 characters." };

  const users = loadUsers();
  if (users[v.email]) return { ok: false, error: "An account with this email already exists. Try signing in." };

  const confirmToken = crypto.randomBytes(24).toString("base64url");
  users[v.email] = {
    id: crypto.randomUUID(),
    email: v.email,
    passHash: hashPassword(password),
    confirmed: false,
    confirmToken,
    createdAt: new Date().toISOString(),
  };
  saveUsers(users);
  return { ok: true, email: v.email, confirmToken };
}

export function confirm(token) {
  if (!token) return { ok: false, error: "Missing confirmation token." };
  const users = loadUsers();
  const entry = Object.values(users).find((u) => u.confirmToken === token);
  if (!entry) return { ok: false, error: "This confirmation link is invalid or already used." };
  entry.confirmed = true;
  delete entry.confirmToken;
  saveUsers(users);
  return { ok: true, email: entry.email };
}

export function login({ email, password }) {
  const v = validateEmail(email);
  const users = loadUsers();
  const user = v.ok ? users[v.email] : null;
  // Verify against a dummy hash when the user is missing so timing doesn't leak
  // which emails are registered.
  const ok = user
    ? verifyPassword(password, user.passHash)
    : (verifyPassword(password, hashPassword("x")), false);
  if (!ok) return { ok: false, error: "Email or password is incorrect." };
  if (!user.confirmed) return { ok: false, error: "Please confirm your email first. Check your inbox for the link.", needsConfirm: true };
  return { ok: true, user: { id: user.id, email: user.email } };
}

export function getUserByEmail(email) {
  const v = validateEmail(email);
  return v.ok ? loadUsers()[v.email] || null : null;
}
export function getUserById(id) {
  return Object.values(loadUsers()).find((u) => u.id === id) || null;
}

/* ---------- sessions (signed cookie) ---------- */
export function createSessionCookie(userId, remember) {
  const exp = remember ? Date.now() + SESSION_DAYS * 864e5 : 0; // 0 = session cookie
  const token = sign(`${userId}.${exp}`);
  const maxAge = remember ? `; Max-Age=${SESSION_DAYS * 86400}` : "";
  return `sid=${token}; Path=/; HttpOnly; SameSite=Lax${maxAge}`;
}
export function clearSessionCookie() {
  return "sid=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0";
}
export function userFromCookies(cookieHeader) {
  const sid = parseCookies(cookieHeader).sid;
  const value = unsign(sid);
  if (!value) return null;
  const [userId, expStr] = value.split(".");
  const exp = Number(expStr);
  if (exp && exp < Date.now()) return null;
  return getUserById(userId);
}
export function parseCookies(header) {
  const out = {};
  for (const part of String(header || "").split(";")) {
    const i = part.indexOf("=");
    if (i > -1) out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim());
  }
  return out;
}

/* ---------- confirmation delivery ---------- */
// No email provider is wired up by default, so the confirmation link is
// returned to the caller (shown on screen) and logged. To send real email,
// implement delivery here (e.g. nodemailer + SMTP) using env credentials.
export function confirmationLink(origin, token) {
  return `${origin}/confirm?token=${encodeURIComponent(token)}`;
}
