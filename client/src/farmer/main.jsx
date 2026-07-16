import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { QueryProvider } from '../shared/api/queryProvider'
import '../index.css'

if (import.meta.env.DEV) {
  import('@axe-core/react').then(({ default: axe }) => {
    axe(React, ReactDOM, 1000)
  }).catch(() => {})
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryProvider>
      <App />
    </QueryProvider>
  </React.StrictMode>
)
