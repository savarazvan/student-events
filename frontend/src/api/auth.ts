import { request } from './client';
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserProfile,
} from '../types';

export function login(data: LoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>('POST', '/auth/login', data, false);
}

export function register(data: RegisterRequest): Promise<UserProfile> {
  return request<UserProfile>('POST', '/auth/register', data, false);
}

export function getMe(): Promise<UserProfile> {
  return request<UserProfile>('GET', '/auth/me');
}
