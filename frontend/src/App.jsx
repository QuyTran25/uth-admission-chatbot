import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import TrangGioiThieu from './TrangGioiThieu.jsx'
import ChatPage from './ChatPage.jsx'
import ChatDetail from './ChatDetail.jsx'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<TrangGioiThieu />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/detail" element={<ChatDetail />} />
      </Routes>
    </Router>
  )
}

export default App
