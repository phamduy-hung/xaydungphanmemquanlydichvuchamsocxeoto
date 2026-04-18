import React, { useState, useEffect } from 'react';

interface FadeInProps {
  children: React.ReactNode;
  delayMs?: number;
  durationMs?: number;
  className?: string;
}

export const FadeIn: React.FC<FadeInProps> = ({ 
  children, 
  delayMs = 0, 
  durationMs = 1000,
  className = ""
}) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delayMs);
    return () => clearTimeout(timer);
  }, [delayMs]);

  return (
    <div 
      className={`transition-opacity ${className}`}
      style={{
        opacity: isVisible ? 1 : 0,
        transitionDuration: `${durationMs}ms`,
      }}
    >
      {children}
    </div>
  );
};
