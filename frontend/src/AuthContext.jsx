import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    const role = localStorage.getItem('role')
    const full_name = localStorage.getItem('full_name')
    const user_id = localStorage.getItem('user_id')
    if (token) setUser({ token, role, full_name, user_id: Number(user_id) })
  }, [])

  const login = (data) => {
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('role', data.role)
    localStorage.setItem('full_name', data.full_name)
    localStorage.setItem('user_id', data.user_id)
    setUser(data)
  }

  const logout = () => {
    localStorage.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
