// Google Photos + Google Drive connect via OAuth 2.0, using only Node built-ins
// and global fetch (Node 18+). Nothing here works until YOU create a free
// Google Cloud OAuth app and provide:
//   GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
// and add "<origin>/auth/google/callback" as an authorized redirect URI.
// See README → "Connect Google Photos & Drive".

import fs from "fs";
import path from "path";
import crypto from "crypto";

const DATA_DIR = path.resolve("data");
const TOKENS_FILE = path.join(DATA_DIR, "google.json");

const SCOPES = {
  photos: "https://www.googleapis.com/auth/photoslibrary.readonly",
  drive: "https://www.googleapis.com/auth/drive.readonly",
};

export function googleConfigured() {
  return Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);
}

function loadTokens() {
  try {
    return JSON.parse(fs.readFileSync(TOKENS_FILE, "utf8"));
  } catch {
    return {};
  }
}
function saveTokens(t) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(TOKENS_FILE, JSON.stringify(t, null, 2), { mode: 0o600 });
}

export function connectionStatus(userId) {
  const t = loadTokens()[userId] || {};
  return {
    configured: googleConfigured(),
    photos: Boolean(t.photos),
    drive: Boolean(t.drive),
  };
}

/** Build the Google consent URL for a service. `state` carries user + service. */
export function authUrl(service, origin, userId) {
  const scope = SCOPES[service];
  if (!scope) throw new Error("Unknown Google service");
  const state = signState({ service, userId, n: crypto.randomBytes(8).toString("hex") });
  const params = new URLSearchParams({
    client_id: process.env.GOOGLE_CLIENT_ID,
    redirect_uri: `${origin}/auth/google/callback`,
    response_type: "code",
    access_type: "offline",
    include_granted_scopes: "true",
    prompt: "consent",
    scope,
    state,
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params}`;
}

function signState(obj) {
  const value = Buffer.from(JSON.stringify(obj)).toString("base64url");
  const mac = crypto.createHmac("sha256", secret()).update(value).digest("base64url");
  return `${value}.${mac}`;
}
export function readState(state) {
  const [value, mac] = String(state || "").split(".");
  if (!value || !mac) return null;
  const expect = crypto.createHmac("sha256", secret()).update(value).digest("base64url");
  const a = Buffer.from(mac), b = Buffer.from(expect);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  try {
    return JSON.parse(Buffer.from(value, "base64url").toString("utf8"));
  } catch {
    return null;
  }
}
function secret() {
  // Reuse the auth secret file so state signing survives restarts.
  const f = path.join(DATA_DIR, "secret.key");
  return fs.existsSync(f) ? fs.readFileSync(f, "utf8").trim() : "dev-secret";
}

/** Exchange an auth code for tokens and persist them for the user+service. */
export async function exchangeCode(code, service, userId, origin) {
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: process.env.GOOGLE_CLIENT_ID,
      client_secret: process.env.GOOGLE_CLIENT_SECRET,
      redirect_uri: `${origin}/auth/google/callback`,
      grant_type: "authorization_code",
    }),
  });
  if (!res.ok) throw new Error(`Google token exchange failed (${res.status})`);
  const data = await res.json();
  const all = loadTokens();
  all[userId] = all[userId] || {};
  all[userId][service] = {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Date.now() + (data.expires_in || 3600) * 1000,
  };
  saveTokens(all);
}

async function accessToken(userId, service) {
  const all = loadTokens();
  const tok = all[userId] && all[userId][service];
  if (!tok) throw new Error(`Google ${service} is not connected.`);
  if (tok.expires_at > Date.now() + 60_000) return tok.access_token;
  if (!tok.refresh_token) return tok.access_token; // best effort
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: process.env.GOOGLE_CLIENT_ID,
      client_secret: process.env.GOOGLE_CLIENT_SECRET,
      refresh_token: tok.refresh_token,
      grant_type: "refresh_token",
    }),
  });
  if (!res.ok) throw new Error("Could not refresh Google access.");
  const data = await res.json();
  tok.access_token = data.access_token;
  tok.expires_at = Date.now() + (data.expires_in || 3600) * 1000;
  saveTokens(all);
  return tok.access_token;
}

export function disconnect(userId, service) {
  const all = loadTokens();
  if (all[userId]) {
    delete all[userId][service];
    saveTokens(all);
  }
}

/** Recent photos from Google Photos as {id, name, thumb} (thumb is a Google URL). */
export async function listPhotos(userId, pageSize = 24) {
  const token = await accessToken(userId, "photos");
  const res = await fetch("https://photoslibrary.googleapis.com/v1/mediaItems?pageSize=" + pageSize, {
    headers: { authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Google Photos error (${res.status})`);
  const data = await res.json();
  return (data.mediaItems || [])
    .filter((m) => (m.mimeType || "").startsWith("image/"))
    .map((m) => ({ id: m.id, name: m.filename, baseUrl: m.baseUrl, thumb: `${m.baseUrl}=w200-h200-c` }));
}

/** Fetch a Photos item at full size and return {media_type, data(base64)}. */
export async function fetchPhoto(userId, baseUrl) {
  const token = await accessToken(userId, "photos"); // token not needed for baseUrl but validates connection
  void token;
  const res = await fetch(`${baseUrl}=w1568-h1568`);
  if (!res.ok) throw new Error("Could not download the photo.");
  return { media_type: "image/jpeg", data: Buffer.from(await res.arrayBuffer()).toString("base64") };
}

/** Recent image files from Google Drive as {id, name, thumb}. */
export async function listDriveImages(userId, pageSize = 24) {
  const token = await accessToken(userId, "drive");
  const q = encodeURIComponent("mimeType contains 'image/' and trashed = false");
  const fields = encodeURIComponent("files(id,name,thumbnailLink,mimeType)");
  const res = await fetch(
    `https://www.googleapis.com/drive/v3/files?q=${q}&pageSize=${pageSize}&orderBy=modifiedTime desc&fields=${fields}`,
    { headers: { authorization: `Bearer ${token}` } },
  );
  if (!res.ok) throw new Error(`Google Drive error (${res.status})`);
  const data = await res.json();
  return (data.files || []).map((f) => ({ id: f.id, name: f.name, mimeType: f.mimeType, thumb: f.thumbnailLink }));
}

/** Download a Drive file and return {media_type, data(base64)}. */
export async function fetchDriveImage(userId, fileId) {
  const token = await accessToken(userId, "drive");
  const res = await fetch(`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(fileId)}?alt=media`, {
    headers: { authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Could not download the Drive file.");
  const type = res.headers.get("content-type") || "image/jpeg";
  return { media_type: type.split(";")[0], data: Buffer.from(await res.arrayBuffer()).toString("base64") };
}
