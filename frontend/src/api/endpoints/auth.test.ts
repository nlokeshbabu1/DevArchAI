import { describe, it, expect, vi, beforeEach } from 'vitest'
import { authApi } from './auth'
import axios from 'axios'

// Mock axios
vi.mock('axios')
const mockedAxios = vi.mocked(axios, true)

describe('Auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('should login successfully', async () => {
      const mockResponse = {
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
      }
      
      mockedAxios.post.mockResolvedValueOnce({ data: mockResponse })
      
      const result = await authApi.login({
        email: 'test@example.com',
        password: 'password123',
      })
      
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/auth/login',
        {
          email: 'test@example.com',
          password: 'password123',
        }
      )
      expect(result).toEqual(mockResponse)
    })

    it('should handle login error', async () => {
      const mockError = new Error('Invalid credentials')
      mockedAxios.post.mockRejectedValueOnce(mockError)
      
      await expect(
        authApi.login({
          email: 'test@example.com',
          password: 'wrong',
        })
      ).rejects.toThrow('Invalid credentials')
    })
  })

  describe('register', () => {
    it('should register successfully', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: { message: 'User created' } })
      
      const result = await authApi.register({
        email: 'test@example.com',
        username: 'testuser',
        password: 'password123',
        organization_name: 'Test Org',
      })
      
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/auth/register',
        {
          email: 'test@example.com',
          username: 'testuser',
          password: 'password123',
          organization_name: 'Test Org',
        }
      )
    })
  })

  describe('getCurrentUser', () => {
    it('should fetch current user', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
      }
      
      mockedAxios.get.mockResolvedValueOnce({ data: mockUser })
      
      const result = await authApi.getCurrentUser()
      
      expect(mockedAxios.get).toHaveBeenCalledWith('/auth/me')
      expect(result).toEqual(mockUser)
    })

    it('should handle fetch user error', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Unauthorized'))
      
      await expect(authApi.getCurrentUser()).rejects.toThrow('Unauthorized')
    })
  })
})
