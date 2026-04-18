import React, { useState, useEffect } from 'react';

interface AnimatedHeadingProps {
  text: string;
  initialDelayMs?: number;
  charDelayMs?: number;
  transitionDurationMs?: number;
  className?: string;
}

export const AnimatedHeading: React.FC<AnimatedHeadingProps> = ({
  text,
  initialDelayMs = 200,
  charDelayMs = 30,
  transitionDurationMs = 500,
  className = ""
}) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setMounted(true);
    }, initialDelayMs);
    return () => clearTimeout(timer);
  }, [initialDelayMs]);

  // Split by literal \n (escaped newline in string)
  const lines = text.split('\n');

  let absoluteCharIndex = 0;

  return (
    <div className={className} style={{ letterSpacing: '-0.04em' }}>
      {lines.map((line, lineIndex) => {
        const chars = line.split('');
        return (
          <div key={lineIndex} className="whitespace-nowrap">
            {chars.map((char, charIndex) => {
              const currentAbsoluteIndex = absoluteCharIndex++;
              const delay = currentAbsoluteIndex * charDelayMs;

              return (
                <span
                  key={`${lineIndex}-${charIndex}`}
                  className="inline-block transition-all"
                  style={{
                    opacity: mounted ? 1 : 0,
                    transform: mounted ? 'translateX(0)' : 'translateX(-18px)',
                    transitionDuration: `${transitionDurationMs}ms`,
                    transitionDelay: `${delay}ms`,
                    // Use non-breaking space so spaces are actually rendered
                    whiteSpace: 'pre',
                  }}
                >
                  {char === ' ' ? '\u00A0' : char}
                </span>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};
