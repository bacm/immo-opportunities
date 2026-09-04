import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { initializeAuth } from './auth'
import './styles.css'

const root = createRoot(document.getElementById('root')!)
root.render(<div className="boot-screen">Connexion sécurisée…</div>)

initializeAuth()
  .then(() => root.render(<StrictMode><App /></StrictMode>))
  .catch(() => root.render(
    <div className="boot-screen error">La session n’a pas pu être établie. Rechargez la page.</div>,
  ))
