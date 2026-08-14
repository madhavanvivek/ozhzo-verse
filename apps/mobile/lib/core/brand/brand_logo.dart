import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'brand_theme.dart';

enum BrandLogoVariant {
  full,
  mark,
  compact,
}

class OzhzoBrandLogo extends StatelessWidget {
  final BrandLogoVariant variant;
  final double? width;
  final double? height;
  final Brightness? brightness;

  const OzhzoBrandLogo({
    super.key,
    this.variant = BrandLogoVariant.full,
    this.width,
    this.height,
    this.brightness,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveBrightness = brightness ?? Theme.of(context).brightness;
    final isDark = effectiveBrightness == Brightness.dark;

    String assetPath;
    double defaultWidth;
    double defaultHeight;

    switch (variant) {
      case BrandLogoVariant.full:
        assetPath = isDark
            ? 'assets/brand/ozhzo-verse-logo-primary-dark.svg'
            : 'assets/brand/ozhzo-verse-logo-primary.svg';
        defaultWidth = 240;
        defaultHeight = 168;
        break;
      case BrandLogoVariant.mark:
        assetPath = isDark
            ? 'assets/brand/ozhzo-mark-dark.svg'
            : 'assets/brand/ozhzo-mark-primary.svg';
        defaultWidth = 64;
        defaultHeight = 64;
        break;
      case BrandLogoVariant.compact:
        assetPath = isDark
            ? 'assets/brand/ozhzo-mark-dark.svg'
            : 'assets/brand/ozhzo-mark-primary.svg';
        defaultWidth = 32;
        defaultHeight = 32;
        break;
    }

    final finalWidth = width ?? defaultWidth;
    final finalHeight = height ?? defaultHeight;

    return SvgPicture.asset(
      assetPath,
      width: finalWidth,
      height: finalHeight,
      fit: BoxFit.contain,
    );
  }
}
