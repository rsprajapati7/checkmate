import chalk from 'chalk';

export const theme = {
  // Raw Hex colors for Ink props compatibility
  colors: {
    gold: '#D4AF37',
    coral: '#D1855C',
    sage: '#8DECB4',
    crimson: '#C0392B',
    sand: '#F6F3EB',
    slate: '#4A4A5A',
  },

  gold: chalk.hex('#D4AF37'),
  coral: chalk.hex('#D1855C'),
  sage: chalk.hex('#8DECB4'),
  crimson: chalk.hex('#C0392B'),
  sand: chalk.hex('#F6F3EB'),
  slate: chalk.hex('#4A4A5A'),
  
  // Highlighting/bold functions
  boldGold: chalk.hex('#D4AF37').bold,
  boldCoral: chalk.hex('#D1855C').bold,
  boldSage: chalk.hex('#8DECB4').bold,
  boldCrimson: chalk.hex('#C0392B').bold,
  boldSand: chalk.hex('#F6F3EB').bold,
  
  // Standard statuses
  success: chalk.hex('#8DECB4'),
  warning: chalk.hex('#D1855C'),
  error: chalk.hex('#C0392B'),
  muted: chalk.hex('#4A4A5A'),
};
