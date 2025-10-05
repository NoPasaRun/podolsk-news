import React, { useState } from 'react'
import { useAuth } from './AuthProvider'
import {requestAuth, verifyAuth} from "@/lib/auth";

export default function AuthPopup({ onClose }) {
  const { login } = useAuth()
  const [step, setStep] = useState(1)
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleRequest = async () => {
    setError(null); setLoading(true)
    try {
      await requestAuth(phone.trim())
      setStep(2)
    } catch (e) {
      setError(e?.message || 'Ошибка')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async () => {
    setError(null); setLoading(true)
    try {
      const tokens = await verifyAuth(phone.trim(), code.trim())
      // сохраняем токены в контекст (и localStorage внутри него)
      login(tokens)
      onClose?.()
    } catch (e) {
      setError(e?.message || 'Ошибка')
    } finally {
      setLoading(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (step === 1 && !loading) handleRequest().then(r => r)
      if (step === 2 && !loading) handleVerify().then(r => r)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onKeyDown={onKeyDown}>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg w-80">
        <h3 className="text-lg font-bold mb-4">
          {step === 1 ? 'Вход / Регистрация' : 'Подтверждение'}
        </h3>

        {step === 1 && (
          <>
            <input
              className="input mb-4"
              placeholder="Телефон"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoFocus
            />
            <button
              onClick={handleRequest}
              className="btn-primary w-full disabled:opacity-60"
              disabled={loading || !phone.trim()}
            >
              {loading ? 'Отправляем...' : 'Получить код'}
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <input
              className="input mb-4"
              placeholder="Код из SMS"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoFocus
            />
            <button
              onClick={handleVerify}
              className="btn-primary w-full disabled:opacity-60"
              disabled={loading || !code.trim()}
            >
              {loading ? 'Проверяем...' : 'Войти'}
            </button>
          </>
        )}

        {error && <div className="mt-3 text-sm text-red-500">{error}</div>}

        <button
          onClick={onClose}
          className="mt-4 w-full text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          Отмена
        </button>
      </div>
    </div>
  )
}
