const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export interface UserResponse {
  id: string;
  email: string;
  name: string | null;
  picture_url: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export async function passwordLogin(
  username: string,
  password: string,
): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string" ? detail : "Login failed",
    );
  }
  return res.json();
}
