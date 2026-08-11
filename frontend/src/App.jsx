import React, { useEffect, useState } from "react";
import { Routes, Route, Link, useNavigate } from "react-router-dom";

import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Problems from "./pages/Problems.jsx";
import ProblemDetail from "./pages/ProblemDetail.jsx";
import Submissions from "./pages/Submissions.jsx";
import Leaderboard from "./pages/Leaderboard.jsx";
import { api } from "./api.js";

export default function App() {
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (localStorage.getItem("token")) {
      api.me().then(setUser).catch(() => localStorage.removeItem("token"));
    }
  }, []);

  function logout() {
    localStorage.removeItem("token");
    setUser(null);
    navigate("/login");
  }

  return (
    <div className="app">
      <nav className="navbar">
        <Link to="/" className="brand">CodeJudge</Link>
        <Link to="/">Problems</Link>
        <Link to="/leaderboard">Leaderboard</Link>
        {user && <Link to="/submissions">My Submissions</Link>}
        <span className="spacer" />
        {user ? (
          <>
            <span className="user-chip">{user.username} · {user.rating} pts</span>
            <button onClick={logout}>Log out</button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </nav>

      <main className="content">
        <Routes>
          <Route path="/" element={<Problems />} />
          <Route path="/problems/:slug" element={<ProblemDetail />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/submissions" element={<Submissions />} />
          <Route path="/login" element={<Login onLogin={setUser} />} />
          <Route path="/register" element={<Register onRegister={setUser} />} />
        </Routes>
      </main>
    </div>
  );
}

