import React from 'react';
import { RegisterForm } from '../components/auth/RegisterForm';
import { ThemeSwitcher } from '../components/layout/ThemeSwitcher';

export const RegisterPage = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas p-4">
      <div className="fixed top-4 right-4 z-50">
        <ThemeSwitcher />
      </div>
      <RegisterForm />
    </div>
  );
};
