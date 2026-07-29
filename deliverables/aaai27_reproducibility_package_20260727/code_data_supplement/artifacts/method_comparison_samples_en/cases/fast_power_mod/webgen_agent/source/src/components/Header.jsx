import React from 'react';
import './Header.css';

export default function Header({ title, family }) {
  return (
    <header className="header">
      <h1 className="header-title">{title}</h1>
      <span className="header-family">{family}</span>
    </header>
  );
}
