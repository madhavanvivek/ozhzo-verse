import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ozhzo_verse_mobile/core/brand/brand_theme.dart';
import 'package:ozhzo_verse_mobile/core/brand/brand_logo.dart';

void main() {
  group('Ozhzo Verse Brand Constants Tests', () {
    test('Tagline matches official standard exactly', () {
      expect(OzhzoBrandTheme.officialTagline, 'Where Home Comes Together.');
    });

    test('Brand colors match approved specifications', () {
      expect(OzhzoBrandTheme.primaryBlue, const Color(0xFF0061FF));
      expect(OzhzoBrandTheme.primaryGreen, const Color(0xFF00B050));
      expect(OzhzoBrandTheme.darkNavy, const Color(0xFF0A2E7A));
    });

    test('Theme configurations contain expected colorScheme tokens', () {
      expect(OzhzoBrandTheme.lightTheme.colorScheme.primary, OzhzoBrandTheme.primaryBlue);
      expect(OzhzoBrandTheme.lightTheme.colorScheme.secondary, OzhzoBrandTheme.primaryGreen);
      expect(OzhzoBrandTheme.darkTheme.brightness, Brightness.dark);
    });
  });
}
