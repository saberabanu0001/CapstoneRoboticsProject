import { StyleSheet, Text, type TextProps } from 'react-native';

import { useThemeColor } from '@/hooks/use-theme-color';
import { SerifFonts } from '@/constants/theme';

export type ThemedTextProps = TextProps & {
  lightColor?: string;
  darkColor?: string;
  type?: 'default' | 'title' | 'defaultSemiBold' | 'subtitle' | 'link';
};

export function ThemedText({
  style,
  lightColor,
  darkColor,
  type = 'default',
  ...rest
}: ThemedTextProps) {
  const color = useThemeColor({ light: lightColor, dark: darkColor }, 'text');

  return (
    <Text
      style={[
        { color },
        type === 'default' ? styles.default : undefined,
        type === 'title' ? styles.title : undefined,
        type === 'defaultSemiBold' ? styles.defaultSemiBold : undefined,
        type === 'subtitle' ? styles.subtitle : undefined,
        type === 'link' ? styles.link : undefined,
        style,
      ]}
      {...rest}
    />
  );
}

const monoRegular = 'JetBrainsMono_400Regular';

const monoSemiBold = 'JetBrainsMono_600SemiBold';

const titleHeading = SerifFonts.bold;

const subtitleHeading = SerifFonts.semiBold;

const styles = StyleSheet.create({
  default: {
    fontFamily: monoRegular,
    fontSize: 16,
    lineHeight: 24,
    includeFontPadding: false,
  },
  defaultSemiBold: {
    fontFamily: monoSemiBold,
    fontSize: 16,
    lineHeight: 24,
    includeFontPadding: false,
  },
  title: {
    fontFamily: titleHeading,
    fontSize: 32,
    lineHeight: 36,
    includeFontPadding: false,
  },
  subtitle: {
    fontFamily: subtitleHeading,
    fontSize: 20,
    lineHeight: 26,
    includeFontPadding: false,
  },
  link: {
    fontFamily: monoSemiBold,
    lineHeight: 30,
    fontSize: 16,
    color: '#5CC8FF',
    includeFontPadding: false,
  },
});
