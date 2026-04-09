import type { ReactElement } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Library from "./pages/Library";
import Login from "./pages/Login";
import Reader from "./pages/Reader";
import Register from "./pages/Register";

function Layout() {
  const { user, loading, logout } = useAuth();
  if (loading) {
    return <div className="shell">Загрузка…</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return (
    <div className="shell">
      <header className="top">
        <h1 className="logo">Техчиталка</h1>
        <nav>
          <span className="user-email">{user.email}</span>
          <button type="button" className="linkish" onClick={logout}>
            Выход
          </button>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}

function PublicOnly({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="shell">Загрузка…</div>;
  }
  if (user) {
    return <Navigate to="/" replace />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicOnly>
            <Login />
          </PublicOnly>
        }
      />
      <Route
        path="/register"
        element={
          <PublicOnly>
            <Register />
          </PublicOnly>
        }
      />
      <Route element={<Layout />}>
        <Route index element={<Library />} />
        <Route path="read/:bookId" element={<Reader />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
