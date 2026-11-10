import React from 'react';
import { LoginForm } from '../components/auth/LoginForm';
import { ThemeSwitcher } from '../components/layout/ThemeSwitcher';

export const LoginPage = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas p-4">
      <div className="fixed top-4 right-4 z-50">
        <ThemeSwitcher />
      </div>
      <LoginForm />
    </div>
  );
};
