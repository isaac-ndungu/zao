import React from 'react'
import ReactDOM from 'react-dom/client'
import { StrictMode } from 'react'
import './index.css'
import App from './App.jsx'

if (import.meta.env.DEV) {
  import('@axe-core/react').then(({ default: axe }) => {
    axe(React, ReactDOM, 1000)
  }).catch(() => {})
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
