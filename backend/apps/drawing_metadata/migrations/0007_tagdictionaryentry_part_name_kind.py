from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("drawing_metadata", "0006_tagdictionaryentry"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tagdictionaryentry",
            name="kind",
            field=models.CharField(
                choices=[
                    ("customer", "客先"),
                    ("equipment_category", "装置カテゴリ"),
                    ("project", "案件"),
                    ("maker", "メーカー"),
                    ("spec", "規格"),
                    ("heat_treatment", "熱処理"),
                    ("part_name", "部品名"),
                ],
                db_index=True,
                max_length=32,
            ),
        ),
    ]
