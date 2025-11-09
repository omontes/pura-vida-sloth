/**
 * Card Component
 *
 * Professional card container with elevation system
 * Supports multiple padding sizes and interactive states
 */

import { HTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';

export type CardPadding = 'none' | 'compact' | 'default' | 'spacious';
export type CardElevation = 'flat' | 'raised' | 'elevated';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: CardPadding;
  elevation?: CardElevation;
  interactive?: boolean;
  children: ReactNode;
}

const paddingStyles: Record<CardPadding, string> = {
  none: 'p-0',
  compact: 'p-4',
  default: 'p-6',
  spacious: 'p-4 sm:p-6 lg:p-8',
};

const elevationStyles: Record<CardElevation, string> = {
  flat: 'bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-gray-800',
  raised:
    'bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-gray-800 shadow-md dark:shadow-dark-md',
  elevated:
    'bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-gray-800 shadow-lg dark:shadow-dark-lg',
};

const baseStyles = 'rounded-lg transition-all duration-200';

export default function Card({
  padding = 'default',
  elevation = 'raised',
  interactive = false,
  className,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={clsx(
        baseStyles,
        paddingStyles[padding],
        elevationStyles[elevation],
        {
          'hover:shadow-xl dark:hover:shadow-dark-xl hover:scale-[1.01] cursor-pointer':
            interactive,
        },
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * CardHeader Component
 *
 * Semantic header section for cards
 */
export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function CardHeader({ className, children, ...props }: CardHeaderProps) {
  return (
    <div
      className={clsx('border-b border-gray-200 dark:border-gray-800 pb-4 mb-6', className)}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * CardTitle Component
 *
 * Typography component for card titles
 */
export interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  children: ReactNode;
  as?: 'h1' | 'h2' | 'h3' | 'h4';
}

export function CardTitle({ as: Component = 'h2', className, children, ...props }: CardTitleProps) {
  const sizeStyles = {
    h1: 'text-3xl',
    h2: 'text-2xl',
    h3: 'text-xl',
    h4: 'text-lg',
  };

  return (
    <Component
      className={clsx(
        'font-bold text-gray-900 dark:text-white tracking-tight',
        sizeStyles[Component],
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}

/**
 * CardDescription Component
 *
 * Typography component for card descriptions
 */
export interface CardDescriptionProps extends HTMLAttributes<HTMLParagraphElement> {
  children: ReactNode;
}

export function CardDescription({ className, children, ...props }: CardDescriptionProps) {
  return (
    <p
      className={clsx('text-base text-gray-600 dark:text-gray-400 mt-2', className)}
      {...props}
    >
      {children}
    </p>
  );
}

/**
 * CardFooter Component
 *
 * Semantic footer section for cards
 */
export interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function CardFooter({ className, children, ...props }: CardFooterProps) {
  return (
    <div
      className={clsx('border-t border-gray-200 dark:border-gray-800 pt-4 mt-6', className)}
      {...props}
    >
      {children}
    </div>
  );
}
