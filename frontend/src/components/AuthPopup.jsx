import React, { useState } from 'react'
import { requestAuth, verifyAuth } from '../api'

export default function AuthPopup({ onClose }) {
  const [step, setStep] = useState(1)
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleRequest = async () => {
    setError(null); setLoading(true)
    try {
      const res = await requestAuth(phone)
      if (!res.ok) throw new Error('Не удалось отправить код')
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
      const res = await verifyAuth(phone, code)
      if (!res.ok) throw new Error('Код не подошёл')
      alert('Успешный вход!')
      onClose()
    } catch (e) {
      setError(e?.message || 'Ошибка')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg w-80">
        <h3 className="text-lg font-bold mb-4">{step === 1 ? 'Вход / Регистрация' : 'Подтверждение'}</h3>

        {step === 1 && (
          <>
            <input
              className="input mb-4"
              placeholder="Телефон"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <button
              onClick={handleRequest}
              className="btn-primary w-full disabled:opacity-60"
              disabled={loading}
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
            />
            <button
              onClick={handleVerify}
              className="btn-primary w-full disabled:opacity-60"
              disabled={loading}
            >
              {loading ? 'Проверяем...' : 'Войти'}
            </button>
          </>
        )}

        {error && <div className="mt-3 text-sm text-red-500">{error}</div>}

        <button onClick={onClose} className="mt-4 w-full text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
          Отмена
        </button>
      </div>
    </div>
  )
}