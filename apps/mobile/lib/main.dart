import 'package:flutter/material.dart';
import 'core/brand/brand_theme.dart';
import 'features/splash/splash_screen.dart';

void main() {
  runApp(const OzhzoVerseApp());
}

class OzhzoVerseApp extends StatelessWidget {
  const OzhzoVerseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Ozhzo Verse',
      debugShowCheckedModeBanner: false,
      theme: OzhzoBrandTheme.lightTheme,
      darkTheme: OzhzoBrandTheme.darkTheme,
      themeMode: ThemeMode.system,
      home: const SplashScreen(),
    );
  }
}
