import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { THEME } from '../constants/theme';
import { CheckStatus, EpistemicStatus } from '../types/analysis';

interface StatusBadgeProps {
  type: 'check' | 'epistemic';
  status: CheckStatus | EpistemicStatus;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, status, size = 'md' }) => {
  let label = '';
  let icon = '';
  let bg = THEME.colors.surfaceLight;
  let text = THEME.colors.textPrimary;
  let border = THEME.colors.border;

  if (type === 'check') {
    switch (status as CheckStatus) {
      case 'pass':
        label = 'PASS';
        icon = '✓';
        bg = THEME.colors.passBg;
        text = THEME.colors.pass;
        border = THEME.colors.passBorder;
        break;
      case 'needs_attention':
        label = 'NEEDS ATTENTION';
        icon = '⚠';
        bg = THEME.colors.warnBg;
        text = THEME.colors.warn;
        border = THEME.colors.warnBorder;
        break;
      case 'fail':
        label = 'ISSUE';
        icon = '✕';
        bg = THEME.colors.failBg;
        text = THEME.colors.fail;
        border = THEME.colors.failBorder;
        break;
    }
  } else {
    // Epistemic Status (FACT vs INFERENCE vs UNKNOWN)
    switch (status as EpistemicStatus) {
      case 'fact':
        label = 'FACT';
        icon = '●';
        bg = THEME.colors.factBg;
        text = THEME.colors.fact;
        border = THEME.colors.fact;
        break;
      case 'inference':
        label = 'INFERENCE';
        icon = '✦';
        bg = THEME.colors.inferenceBg;
        text = THEME.colors.inference;
        border = THEME.colors.inference;
        break;
      case 'unknown':
        label = 'UNKNOWN';
        icon = '○';
        bg = THEME.colors.unknownBg;
        text = THEME.colors.unknown;
        border = THEME.colors.unknown;
        break;
    }
  }

  const isSmall = size === 'sm';

  return (
    <View style={[styles.badge, { backgroundColor: bg, borderColor: border }, isSmall && styles.badgeSmall]}>
      <Text style={[styles.icon, { color: text }, isSmall && styles.iconSmall]}>{icon}</Text>
      <Text style={[styles.label, { color: text }, isSmall && styles.labelSmall]}>{label}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: THEME.borderRadius.sm,
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
  badgeSmall: {
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  icon: {
    fontSize: 11,
    fontWeight: '800',
    marginRight: 4,
  },
  iconSmall: {
    fontSize: 9,
    marginRight: 3,
  },
  label: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  labelSmall: {
    fontSize: 9,
    letterSpacing: 0.3,
  },
});
