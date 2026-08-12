import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api.js";

export default function Register({ onRegister }) {
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  function update(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await api.register(form);
      const { access_token } = await api.login({ username: form.username, password: form.password });
      localStorage.setItem("token", access_token);
      const me = await api.me();
      onRegister(me);
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="card auth-card">
      <h2>Create an account</h2>
      <form onSubmit={handleSubmit}>
        <label>Username</label>
        <input value={form.username} onChange={update("username")} required minLength={3} />
        <label>Email</label>
        <input type="email" value={form.email} onChange={update("email")} required />
        <label>Password</label>
        <input type="password" value={form.password} onChange={update("password")} required minLength={8} />
        {error && <p className="error">{error}</p>}
        <button type="submit">Register</button>
      </form>
      <p>Already have an account? <Link to="/login">Log in</Link></p>
    </div>
  );
}

