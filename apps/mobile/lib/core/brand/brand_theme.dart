import 'package:flutter/material.dart';

/// Ozhzo Verse Frozen Brand Design Tokens
class OzhzoBrandTheme {
  // Official Approved Brand Colors
  static const Color primaryBlue = Color(0xFF0061FF);
  static const Color primaryGreen = Color(0xFF00B050);
  static const Color darkNavy = Color(0xFF0A2E7A);
  
  static const Color bgLight = Color(0xFFF8FAFC);
  static const Color bgDark = Color(0xFF090D16);
  static const Color surfaceCardLight = Color(0xFFFFFFFF);
  static const Color surfaceCardDark = Color(0xFF0F172A);

  static const Color textPrimaryLight = Color(0xFF0F172A);
  static const Color textSecondaryLight = Color(0xFF64748B);
  static const Color textPrimaryDark = Color(0xFFF8FAFC);
  static const Color textSecondaryDark = Color(0xFF94A3B8);

  // Official Tagline Standard
  static const String officialTagline = 'Where Home Comes Together.';

  static ThemeData lightTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    scaffoldBackgroundColor: bgLight,
    colorScheme: const ColorScheme.light(
      primary: primaryBlue,
      secondary: primaryGreen,
      surface: surfaceCardLight,
      background: bgLight,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: surfaceCardLight,
      elevation: 0,
      scrolledUnderElevation: 1,
      titleTextStyle: TextStyle(
        color: textPrimaryLight,
        fontSize: 18,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.2,
      ),
    ),
  );

  static ThemeData darkTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: bgDark,
    colorScheme: const ColorScheme.dark(
      primary: Color(0xFF38BDF8),
      secondary: Color(0xFF34D399),
      surface: surfaceCardDark,
      background: bgDark,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: surfaceCardDark,
      elevation: 0,
      scrolledUnderElevation: 1,
      titleTextStyle: TextStyle(
        color: textPrimaryDark,
        fontSize: 18,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.2,
      ),
    ),
  );
}
