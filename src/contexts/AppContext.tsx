'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface AppState {
  language: string
  phone: string
  name: string
  age: string
  village: string
  crops: string[]
  quantity: number
  token: string | null
  farmerId: number | null
  latitude: number | null
  longitude: number | null
  villageName: string | null
}

interface AppContextType {
  state: AppState
  setLanguage: (lang: string) => void
  setPhone: (phone: string) => void
  setProfile: (name: string, age: string, village: string) => void
  setCrops: (crops: string[]) => void
  setQuantity: (quantity: number) => void
  setToken: (token: string | null) => void
  setFarmerId: (id: number | null) => void
  setLocation: (lat: number, lon: number, village?: string) => void
}

const AppContext = createContext<AppContextType | undefined>(undefined)

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>({
    language: 'hi',
    phone: '',
    name: '',
    age: '',
    village: '',
    crops: ['Wheat'],
    quantity: 10,
    token: null,
    farmerId: null,
    latitude: null,
    longitude: null,
    villageName: null,
  })

  useEffect(() => {
    const savedToken = localStorage.getItem('farmo_token')
    const savedFarmerId = localStorage.getItem('farmer_id')
    setState((s) => ({
      ...s,
      token: savedToken ?? s.token,
      farmerId: savedFarmerId ? Number(savedFarmerId) : s.farmerId,
    }))
  }, [])

  const setLanguage = (language: string) => setState((s) => ({ ...s, language }))
  const setPhone = (phone: string) => setState((s) => ({ ...s, phone }))
  const setProfile = (name: string, age: string, village: string) =>
    setState((s) => ({ ...s, name, age, village }))
  const setCrops = (crops: string[]) => setState((s) => ({ ...s, crops }))
  const setQuantity = (quantity: number) => setState((s) => ({ ...s, quantity }))

  const setToken = (token: string | null) => {
    if (token) {
      localStorage.setItem('farmo_token', token)
    } else {
      localStorage.removeItem('farmo_token')
    }
    setState((s) => ({ ...s, token }))
  }

  const setFarmerId = (id: number | null) => {
    if (id !== null) {
      localStorage.setItem('farmer_id', String(id))
    } else {
      localStorage.removeItem('farmer_id')
    }
    setState((s) => ({ ...s, farmerId: id }))
  }

  const setLocation = (lat: number, lon: number, village?: string) =>
    setState((s) => ({
      ...s,
      latitude: lat,
      longitude: lon,
      villageName: village ?? s.villageName,
    }))

  return (
    <AppContext.Provider
      value={{
        state,
        setLanguage,
        setPhone,
        setProfile,
        setCrops,
        setQuantity,
        setToken,
        setFarmerId,
        setLocation,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) throw new Error('useApp must be used within AppProvider')
  return context
}
