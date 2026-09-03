import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// إعداد التوقيع — من متغيرات البيئة أولاً (CI)، ثم من `android/key.properties`
// المحلي المستثنى من git.
//
// المادة ٥-٣: الأسرار خارج المستودع، ولا تُنسخ بين البيئات. لا مسار مفتاح ولا
// كلمة سرّ ولا اسم مستعار مكتوب في هذا الملف ولا في أي ملف مرفوع.
val keyProperties = Properties().apply {
    val file = rootProject.file("key.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}

fun signingSecret(variable: String, property: String): String? =
    System.getenv(variable) ?: keyProperties.getProperty(property)

val keystorePath = signingSecret("HARAJ_KEYSTORE_PATH", "storeFile")
val hasReleaseKeystore = keystorePath != null

// بناء إنتاج موقَّع بمفتاح التصحيح عطبٌ صامت: الحزمة تُبنى وتبدو سليمة، ومفتاح
// التصحيح يملكه كل من استنسخ المستودع. الفشل هنا أرخص من اكتشافه بعد التوزيع.
if (!hasReleaseKeystore) {
    gradle.taskGraph.whenReady {
        val productionRelease = allTasks.any {
            it.name.startsWith("assembleProdRelease") ||
                it.name.startsWith("bundleProdRelease")
        }
        if (productionRelease) {
            throw GradleException(
                "بناء إنتاج بلا مفتاح توقيع. اضبط HARAJ_KEYSTORE_PATH و" +
                    "HARAJ_KEYSTORE_PASSWORD و HARAJ_KEY_ALIAS و HARAJ_KEY_PASSWORD " +
                    "في البيئة، أو أنشئ android/key.properties محلياً (وهو مستثنى من git)."
            )
        }
    }
}

android {
    namespace = "sa.harajwahed.haraj_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "sa.harajwahed.haraj_mobile"

        // معيار القبول H1: «أندرويد 9+». الرقم مكتوب هنا لا متروكاً لافتراض
        // الأداة، فترقية Flutter لا تحرّك النطاق المتعاقَد عليه بلا قرار.
        minSdk = 28
        targetSdk = flutter.targetSdkVersion

        // رقم الإصدار واسمه من `pubspec.yaml`، ويُتجاوَزان في النشر بـ
        // `--build-number` و`--build-name` (انظر tool/build_android.sh).
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    // المادة ٥-٦: كل بيئة تعرف نفسها. لكل بيئة معرّف حزمة واسم مختلفان، فيمكن
    // تثبيت التجريب والإنتاج على جهاز واحد، ولا يظنّ مختبِر أنه على أحدهما وهو
    // على الآخر. اللافتة داخل التطبيق (T718) هي الطبقة الثانية من الجواب نفسه.
    flavorDimensions += "environment"
    productFlavors {
        create("dev") {
            dimension = "environment"
            applicationIdSuffix = ".dev"
            versionNameSuffix = "-dev"
            resValue("string", "app_name", "حراج (تطوير)")
        }
        create("staging") {
            dimension = "environment"
            applicationIdSuffix = ".staging"
            versionNameSuffix = "-staging"
            resValue("string", "app_name", "حراج (تجريب)")
        }
        create("prod") {
            dimension = "environment"
            resValue("string", "app_name", "حراج واحد")
        }
    }

    signingConfigs {
        create("release") {
            if (keystorePath != null) {
                storeFile = file(keystorePath)
                storePassword = signingSecret("HARAJ_KEYSTORE_PASSWORD", "storePassword")
                keyAlias = signingSecret("HARAJ_KEY_ALIAS", "keyAlias")
                keyPassword = signingSecret("HARAJ_KEY_PASSWORD", "keyPassword")
            }
        }
    }

    buildTypes {
        release {
            // dev/staging يقعان على مفتاح التصحيح كي يعمل `flutter run --release`
            // على جهاز مطوّر بلا أسرار؛ وprod يفشل قبل الوصول إلى هنا (أعلاه).
            signingConfig = if (hasReleaseKeystore) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

// إعداد Firebase لكل بيئة يوضع في `app/src/<flavor>/google-services.json` وقت
// النشر، ولا يدخل المستودع (المادة ٥-٣).
//
// التطبيق مشروط بوجوده عمداً: بناء محلي بلا الملف يعمل وتُطفأ الإشعارات وحدها
// (`data/notifications/push_service_factory.dart`)، بدل أن يفشل بناء كل من
// استنسخ المستودع على ملف لا يملكه.
val hasFirebaseConfig =
    file("google-services.json").exists() ||
        fileTree("src") { include("**/google-services.json") }.files.isNotEmpty()

if (hasFirebaseConfig) {
    apply(plugin = "com.google.gms.google-services")
}
