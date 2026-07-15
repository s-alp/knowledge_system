param(
    [string]$OutputDir = 'C:\Users\s-iwata\Desktop\knowledge_system\ナレッジシステムお披露目会向け\お披露目会_作成資料_20260601\pdm_csv_exhibition_2026-06-03\20260603_ナレッジシステム用CSV'
)

$PSDefaultParameterValues['*:Encoding'] = 'utf8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Utf8Csv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [object[]]$Rows
    )

    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }

    $Rows | Export-Csv -LiteralPath $Path -NoTypeInformation -Encoding utf8
}

function New-OrderedObject {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Data
    )

    return [PSCustomObject]$Data
}

function New-PartTemplate {
    param(
        [string]$Suffix,
        [string]$Category,
        [string]$Material,
        [string]$Surface,
        [string]$Environment,
        [string]$Importance
    )

    return [PSCustomObject]@{
        Suffix       = $Suffix
        Category     = $Category
        Material     = $Material
        Surface      = $Surface
        Environment  = $Environment
        Importance   = $Importance
    }
}

function New-DisplayName {
    param(
        [string]$LastName,
        [string]$FirstName
    )

    return ('{0} {1}' -f $LastName, $FirstName)
}

function New-CustomerRecord {
    param(
        [string]$CompanyName,
        [string]$Department,
        [string]$LastName,
        [string]$FirstName,
        [string]$Title,
        [string]$Email
    )

    return [PSCustomObject]@{
        CompanyName        = $CompanyName
        Department         = $Department
        CustomerName       = ('{0} {1}' -f $CompanyName, $Department)
        ContactLastName    = $LastName
        ContactFirstName   = $FirstName
        ContactDisplayName = (New-DisplayName -LastName $LastName -FirstName $FirstName)
        ContactTitle       = $Title
        ContactEmail       = $Email
    }
}

function New-UserRecord {
    param(
        [string]$LastName,
        [string]$FirstName,
        [string]$Department,
        [string]$Title,
        [string]$Email
    )

    return [PSCustomObject]@{
        LastName    = $LastName
        FirstName   = $FirstName
        DisplayName = (New-DisplayName -LastName $LastName -FirstName $FirstName)
        Department  = $Department
        Title       = $Title
        Email       = $Email
    }
}

function Get-ProductPartTemplates {
    param(
        [string]$TemplateKey
    )

    switch ($TemplateKey) {
        'safety' {
            return @(
                (New-PartTemplate '支柱フレーム' '板金部品' 'SS400' '粉体塗装' '一般屋内' 'A'),
                (New-PartTemplate '扉ブラケット' '板金部品' 'SS400' '粉体塗装' '一般屋内' 'B'),
                (New-PartTemplate '透明保護パネル' '樹脂部品' 'ポリカーボネート' '' '一般屋内' 'A'),
                (New-PartTemplate 'ドアロックプレート' '安全部品' 'SUS304' '' '一般屋内' 'A'),
                (New-PartTemplate '安全スイッチベース' '安全部品' 'A5052' 'アルマイト' '一般屋内' 'A'),
                (New-PartTemplate 'ケーブル引込カバー' '電装部品' 'SPCC' '粉体塗装' '一般屋内' 'B'),
                (New-PartTemplate '点検窓フレーム' '板金部品' 'A5052' 'アルマイト' '一般屋内' 'B'),
                (New-PartTemplate '警告銘板ベース' '安全部品' 'SUS304' '' '一般屋内' 'C')
            )
        }
        'control' {
            return @(
                (New-PartTemplate '制御盤ベース' '板金部品' 'SPCC' '粉体塗装' '一般屋内' 'A'),
                (New-PartTemplate '盤内取付板' '板金部品' 'SPCC' '亜鉛メッキ' '一般屋内' 'A'),
                (New-PartTemplate '端子台ブラケット' '電装部品' 'SPCC' '亜鉛メッキ' '一般屋内' 'B'),
                (New-PartTemplate '配線ダクトカバー' '電装部品' 'ABS' '' '一般屋内' 'B'),
                (New-PartTemplate '操作盤扉' '板金部品' 'SPCC' '粉体塗装' '一般屋内' 'A'),
                (New-PartTemplate '非常停止ボタン座' '安全部品' 'A5052' 'アルマイト' '一般屋内' 'A'),
                (New-PartTemplate 'ケーブルブッシュプレート' '電装部品' 'SPCC' '亜鉛メッキ' '一般屋内' 'B'),
                (New-PartTemplate '銘板ホルダ' '電装部品' 'ABS' '' '一般屋内' 'C')
            )
        }
        'conveyor' {
            return @(
                (New-PartTemplate '駆動ローラ' '搬送部品' 'S45C' '黒染め' '一般屋内' 'A'),
                (New-PartTemplate '従動ローラ' '搬送部品' 'S45C' '黒染め' '一般屋内' 'A'),
                (New-PartTemplate 'サイドレール' '搬送部品' 'A6063' 'アルマイト' '一般屋内' 'B'),
                (New-PartTemplate 'テンショナブラケット' '搬送部品' 'SS400' '粉体塗装' '一般屋内' 'B'),
                (New-PartTemplate 'パレットストッパ' '搬送部品' 'S45C' '無電解ニッケル' '一般屋内' 'A'),
                (New-PartTemplate 'フレーム支柱' '板金部品' 'SS400' '粉体塗装' '一般屋内' 'B'),
                (New-PartTemplate '取付脚' '板金部品' 'SS400' '粉体塗装' '一般屋内' 'B'),
                (New-PartTemplate 'ベルトガイド' '搬送部品' 'UHMW-PE' '' '一般屋内' 'B')
            )
        }
        'inspection' {
            return @(
                (New-PartTemplate 'カメラブラケット' 'センサ部品' 'A5052' 'アルマイト' '一般屋内' 'A'),
                (New-PartTemplate '照明ユニットベース' 'センサ部品' 'A5052' 'アルマイト' '一般屋内' 'A'),
                (New-PartTemplate '検査治具プレート' '治具部品' 'S50C' '無電解ニッケル' '一般屋内' 'A'),
                (New-PartTemplate 'センサホルダ' 'センサ部品' 'POM' '' '一般屋内' 'B'),
                (New-PartTemplate '調整スペーサ' '治具部品' 'SUS304' '' '一般屋内' 'C'),
                (New-PartTemplate 'ワーク受け' '治具部品' 'MCナイロン' '' '一般屋内' 'A'),
                (New-PartTemplate '配線ガイド' '電装部品' 'ABS' '' '一般屋内' 'C'),
                (New-PartTemplate '遮光カバー' '板金部品' 'SPCC' '黒塗装' '一般屋内' 'B')
            )
        }
        'fluid' {
            return @(
                (New-PartTemplate 'ノズルマニホールド' 'ノズル部品' 'SUS304' '電解研磨' '水・クーラント' 'A'),
                (New-PartTemplate 'ノズルブロック' 'ノズル部品' 'SUS303' '電解研磨' '水・クーラント' 'A'),
                (New-PartTemplate 'スプレーブラケット' 'ノズル部品' 'SUS304' '' '水・クーラント' 'B'),
                (New-PartTemplate 'クーラント配管' '流体部品' 'SUS304' '' '水・クーラント' 'A'),
                (New-PartTemplate '集液パン' '流体部品' 'SUS304' '' '水・クーラント' 'B'),
                (New-PartTemplate '洗浄カバー' '板金部品' 'SUS304' '' '水・クーラント' 'B'),
                (New-PartTemplate 'ドレンブロック' '流体部品' 'SUS303' '' '水・クーラント' 'B'),
                (New-PartTemplate 'メンテナンスハンドル' '治具部品' 'SUS304' '' '水・クーラント' 'C')
            )
        }
        'locating' {
            return @(
                (New-PartTemplate '基準ブロック' '治具部品' 'SKD11' '硬質クロム' '一般屋内' 'A'),
                (New-PartTemplate '位置決めピン' '治具部品' 'SKD11' '硬質クロム' '一般屋内' 'A'),
                (New-PartTemplate 'クランププレート' '治具部品' 'S50C' '黒染め' '一般屋内' 'A'),
                (New-PartTemplate '押さえアーム' '治具部品' 'S45C' '黒染め' '一般屋内' 'A'),
                (New-PartTemplate '逃げプレート' '治具部品' 'A5052' 'アルマイト' '一般屋内' 'B'),
                (New-PartTemplate 'センサプレート' 'センサ部品' 'A5052' 'アルマイト' '一般屋内' 'B'),
                (New-PartTemplate 'ガイドブッシュ' '駆動部品' 'SUJ2' '' '一般屋内' 'B'),
                (New-PartTemplate '調整シム' '締結部品' 'SUS304' '' '一般屋内' 'C')
            )
        }
        'lifting' {
            return @(
                (New-PartTemplate 'リフターベース' '搬送部品' 'SS400' '粉体塗装' '一般屋内' 'A'),
                (New-PartTemplate 'シリンダブラケット' '搬送部品' 'SS400' '粉体塗装' '一般屋内' 'A'),
                (New-PartTemplate 'ガイドシャフト' '駆動部品' 'SUJ2' '' '一般屋内' 'A'),
                (New-PartTemplate 'ストッパプレート' '搬送部品' 'S45C' '黒染め' '一般屋内' 'B'),
                (New-PartTemplate 'ホースクランプ' '流体部品' 'SUS304' '' '一般屋内' 'B'),
                (New-PartTemplate 'ケーブルベアブラケット' '電装部品' 'SPCC' '粉体塗装' '一般屋内' 'B'),
                (New-PartTemplate '上昇フレーム' '板金部品' 'SS400' '粉体塗装' '一般屋内' 'A'),
                (New-PartTemplate '着座パッド' '樹脂部品' 'ウレタン' '' '一般屋内' 'C')
            )
        }
        'tooling' {
            return @(
                (New-PartTemplate 'ツーリングベース' '治具部品' 'FC250' '' '一般屋内' 'A'),
                (New-PartTemplate '交換プレート' '治具部品' 'A5052' 'アルマイト' '一般屋内' 'A'),
                (New-PartTemplate '位置決めブロック' '治具部品' 'SKD11' '硬質クロム' '一般屋内' 'A'),
                (New-PartTemplate 'クランプレバー座' '治具部品' 'S45C' '黒染め' '一般屋内' 'B'),
                (New-PartTemplate 'ピンホルダ' '治具部品' 'S50C' '黒染め' '一般屋内' 'B'),
                (New-PartTemplate '交換用スペーサ' '締結部品' 'SUS304' '' '一般屋内' 'C'),
                (New-PartTemplate 'ケーブル逃げカバー' '板金部品' 'SPCC' '粉体塗装' '一般屋内' 'C'),
                (New-PartTemplate '識別銘板' '樹脂部品' 'ABS' '' '一般屋内' 'C')
            )
        }
        'feeding' {
            return @(
                (New-PartTemplate '部品供給シュート' '搬送部品' 'SUS304' 'バフ研磨' '一般屋内' 'A'),
                (New-PartTemplate '整列ガイド' '搬送部品' 'POM' '' '一般屋内' 'B'),
                (New-PartTemplate 'ストッパユニット' '搬送部品' 'S45C' '黒染め' '一般屋内' 'A'),
                (New-PartTemplate 'ホッパベース' '板金部品' 'SPCC' '粉体塗装' '一般屋内' 'A'),
                (New-PartTemplate '振動フィーダブラケット' '搬送部品' 'SS400' '粉体塗装' '一般屋内' 'B'),
                (New-PartTemplate '投入センサ台' 'センサ部品' 'A5052' 'アルマイト' '一般屋内' 'B'),
                (New-PartTemplate '残量確認窓' '樹脂部品' 'ポリカーボネート' '' '一般屋内' 'C'),
                (New-PartTemplate 'ホッパカバー' '板金部品' 'SPCC' '粉体塗装' '一般屋内' 'C')
            )
        }
        default {
            throw "Unknown template key: $TemplateKey"
        }
    }
}

$customers = @(
    (New-CustomerRecord -CompanyName '蒼峰自動機株式会社' -Department '生産技術部' -LastName '篠岡' -FirstName '悠真' -Title '主任' -Email 'yuma.shinooka@soho-automation.example.jp'),
    (New-CustomerRecord -CompanyName '蒼峰自動機株式会社' -Department '駆動開発部' -LastName '綾部' -FirstName '海斗' -Title '係長' -Email 'kaito.ayabe@soho-automation.example.jp'),
    (New-CustomerRecord -CompanyName '白嶺精機工業株式会社' -Department '第一製造部' -LastName '真壁' -FirstName '悠人' -Title '主任' -Email 'yuto.makabe@hakurei-seiki.example.jp'),
    (New-CustomerRecord -CompanyName '白嶺精機工業株式会社' -Department '品質保証部' -LastName '倉橋' -FirstName '玲央' -Title '課長補佐' -Email 'reo.kurahashi@hakurei-seiki.example.jp'),
    (New-CustomerRecord -CompanyName '東和機装システム株式会社' -Department '生産革新部' -LastName '水上' -FirstName '拓海' -Title '主任' -Email 'takumi.mizukami@towa-kiso.example.jp'),
    (New-CustomerRecord -CompanyName '東和機装システム株式会社' -Department '電動化設備部' -LastName '川北' -FirstName '陽向' -Title '課長' -Email 'hinata.kawakita@towa-kiso.example.jp'),
    (New-CustomerRecord -CompanyName '高津ラインテック株式会社' -Department '設備開発課' -LastName '高瀬' -FirstName '蒼真' -Title '主任' -Email 'soma.takase@takatsu-linetech.example.jp'),
    (New-CustomerRecord -CompanyName '高津ラインテック株式会社' -Department '量産準備課' -LastName '新居' -FirstName '遥斗' -Title '係長' -Email 'haruto.nii@takatsu-linetech.example.jp'),
    (New-CustomerRecord -CompanyName '瑞穂ファクトリーオート株式会社' -Department '工程設計部' -LastName '森崎' -FirstName '湊人' -Title '主任' -Email 'minato.morisaki@mizuho-factory.example.jp'),
    (New-CustomerRecord -CompanyName '瑞穂ファクトリーオート株式会社' -Department '品質技術部' -LastName '里見' -FirstName '結人' -Title '課長補佐' -Email 'yuito.satomi@mizuho-factory.example.jp')
)

$internalCompanyName = '蒼雲機装株式会社'

$internalUsers = @(
    (New-UserRecord -LastName '柊木' -FirstName '智也' -Department '技術本部 機械設計一部' -Title '主任' -Email 'tomoya.hiiragi@soun-kiso.example.jp'),
    (New-UserRecord -LastName '長岡' -FirstName '健吾' -Department '技術本部 機械設計一部' -Title '係長' -Email 'kengo.nagaoka@soun-kiso.example.jp'),
    (New-UserRecord -LastName '奥谷' -FirstName '直樹' -Department '技術本部 制御設計部' -Title '主任' -Email 'naoki.okutani@soun-kiso.example.jp'),
    (New-UserRecord -LastName '牧田' -FirstName '恒一' -Department '技術本部 制御設計部' -Title '課長' -Email 'koichi.makita@soun-kiso.example.jp'),
    (New-UserRecord -LastName '常盤' -FirstName '颯太' -Department '技術本部 開発設計部' -Title '主任' -Email 'sota.tokiwa@soun-kiso.example.jp'),
    (New-UserRecord -LastName '雪村' -FirstName '亮介' -Department '生産技術本部 設備開発部' -Title '係長' -Email 'ryosuke.yukimura@soun-kiso.example.jp')
)

$partCategories = @(
    '締結部品',
    '駆動部品',
    '搬送部品',
    'センサ部品',
    '制御部品',
    'ノズル部品',
    '流体部品',
    '安全部品',
    '板金部品',
    '治具部品',
    '電装部品',
    '樹脂部品'
)

$projects = @(
    [PSCustomObject]@{ Code = 'PRJ260601'; Name = 'PJ-260601 EV二輪モータケース洗浄ライン'; Customer = $customers[0].CustomerName; Contact = $customers[0].ContactDisplayName; Status = '着手中'; Manager = $internalUsers[0].DisplayName; Start = '2026-04-01'; PlannedEnd = '2026-10-31'; End = ''; Note = '展示会向け創作案件。EV二輪向け洗浄ライン。' },
    [PSCustomObject]@{ Code = 'PRJ260602'; Name = 'PJ-260602 小径シャフト自動計測セル'; Customer = $customers[1].CustomerName; Contact = $customers[1].ContactDisplayName; Status = '着手中'; Manager = $internalUsers[1].DisplayName; Start = '2026-04-15'; PlannedEnd = '2026-09-30'; End = ''; Note = '展示会向け創作案件。小径シャフトの寸法計測セル。' },
    [PSCustomObject]@{ Code = 'PRJ260603'; Name = 'PJ-260603 バルブボディ外観検査ライン'; Customer = $customers[2].CustomerName; Contact = $customers[2].ContactDisplayName; Status = '着手中'; Manager = $internalUsers[2].DisplayName; Start = '2026-03-20'; PlannedEnd = '2026-11-15'; End = ''; Note = '展示会向け創作案件。外観検査と洗浄を組み合わせたライン。' },
    [PSCustomObject]@{ Code = 'PRJ260604'; Name = 'PJ-260604 冷却プレート組立ライン'; Customer = $customers[3].CustomerName; Contact = $customers[3].ContactDisplayName; Status = '承認待ち'; Manager = $internalUsers[3].DisplayName; Start = '2026-05-01'; PlannedEnd = '2026-12-20'; End = ''; Note = '展示会向け創作案件。冷却プレートの組立工程。' },
    [PSCustomObject]@{ Code = 'PRJ260605'; Name = 'PJ-260605 ブレーキブラケット加工セル'; Customer = $customers[4].CustomerName; Contact = $customers[4].ContactDisplayName; Status = '着手中'; Manager = $internalUsers[4].DisplayName; Start = '2026-02-10'; PlannedEnd = '2026-08-31'; End = ''; Note = '展示会向け創作案件。切削と洗浄の一体セル。' },
    [PSCustomObject]@{ Code = 'PRJ260606'; Name = 'PJ-260606 バッテリケース漏れ検査設備'; Customer = $customers[5].CustomerName; Contact = $customers[5].ContactDisplayName; Status = '承認待ち'; Manager = $internalUsers[5].DisplayName; Start = '2026-04-10'; PlannedEnd = '2026-11-30'; End = ''; Note = '展示会向け創作案件。漏れ検査と結果記録を実施。' },
    [PSCustomObject]@{ Code = 'PRJ260607'; Name = 'PJ-260607 シール圧入・寸法確認セル'; Customer = $customers[6].CustomerName; Contact = $customers[6].ContactDisplayName; Status = '着手中'; Manager = $internalUsers[0].DisplayName; Start = '2026-05-12'; PlannedEnd = '2026-10-10'; End = ''; Note = '展示会向け創作案件。圧入と画像確認を実施。' },
    [PSCustomObject]@{ Code = 'PRJ260608'; Name = 'PJ-260608 ロータ搬送パレット更新案件'; Customer = $customers[7].CustomerName; Contact = $customers[7].ContactDisplayName; Status = '製作中'; Manager = $internalUsers[1].DisplayName; Start = '2026-01-20'; PlannedEnd = '2026-07-31'; End = ''; Note = '展示会向け創作案件。既設搬送ラインの更新。' },
    [PSCustomObject]@{ Code = 'PRJ260609'; Name = 'PJ-260609 ハウジング反転搬送ユニット'; Customer = $customers[8].CustomerName; Contact = $customers[8].ContactDisplayName; Status = '着手中'; Manager = $internalUsers[2].DisplayName; Start = '2026-03-01'; PlannedEnd = '2026-09-15'; End = ''; Note = '展示会向け創作案件。ワーク反転搬送の追加ユニット。' },
    [PSCustomObject]@{ Code = 'PRJ260610'; Name = 'PJ-260610 出荷前最終検査ライン'; Customer = $customers[9].CustomerName; Contact = $customers[9].ContactDisplayName; Status = '承認待ち'; Manager = $internalUsers[3].DisplayName; Start = '2026-05-20'; PlannedEnd = '2026-12-15'; End = ''; Note = '展示会向け創作案件。最終検査と結果保存を実施。' }
)

$products = @(
    [PSCustomObject]@{ Code = 'PROD001'; Name = '安全囲いユニット'; Category = '治具'; Type = '標準品'; Phase = '設計'; Status = '承認待ち'; Owner = $internalUsers[0].DisplayName; Note = '複数案件で共通利用する安全囲い。'; Drive = ''; Power = ''; Line = '共通モジュール'; Location = '設備外周'; TemplateKey = 'safety'; Shared = $true; Tags = @('safety') },
    [PSCustomObject]@{ Code = 'PROD002'; Name = '制御盤ユニット'; Category = '制御盤'; Type = '標準品'; Phase = '設計'; Status = '設計中'; Owner = $internalUsers[1].DisplayName; Note = '複数案件で共通利用する制御盤。'; Drive = ''; Power = 'AC200V'; Line = '共通モジュール'; Location = '設備側面'; TemplateKey = 'control'; Shared = $true; Tags = @('control') },
    [PSCustomObject]@{ Code = 'PROD003'; Name = '搬送コンベアユニット'; Category = 'コンベア'; Type = '標準品'; Phase = '製造・組立'; Status = '製作中'; Owner = $internalUsers[2].DisplayName; Note = '複数案件で共通利用する搬送モジュール。'; Drive = 'サーボモータ'; Power = 'AC200V'; Line = '共通モジュール'; Location = '設備中央'; TemplateKey = 'conveyor'; Shared = $true; Tags = @('conveyor') },
    [PSCustomObject]@{ Code = 'PROD004'; Name = '画像検査ユニット'; Category = '検査装置'; Type = '標準品'; Phase = '設計'; Status = '設計中'; Owner = $internalUsers[3].DisplayName; Note = '複数案件で共通利用する画像検査モジュール。'; Drive = '電動調整'; Power = 'DC24V'; Line = '共通モジュール'; Location = '検査ブース'; TemplateKey = 'inspection'; Shared = $true; Tags = @('inspection') },
    [PSCustomObject]@{ Code = 'PROD005'; Name = '集塵ダクトユニット'; Category = '搬送装置'; Type = '標準品'; Phase = '設計'; Status = '承認待ち'; Owner = $internalUsers[4].DisplayName; Note = '加工・洗浄設備向けの共通集塵ユニット。'; Drive = ''; Power = ''; Line = '共通モジュール'; Location = '設備上部'; TemplateKey = 'fluid'; Shared = $true; Tags = @('duct','fluid') },
    [PSCustomObject]@{ Code = 'PROD006'; Name = 'ノズル洗浄ユニット'; Category = '加工機'; Type = '標準品'; Phase = '設計'; Status = '設計中'; Owner = $internalUsers[5].DisplayName; Note = 'クーラント・洗浄液を使う共通モジュール。'; Drive = 'エアシリンダ'; Power = 'DC24V'; Line = '共通モジュール'; Location = '洗浄槽周辺'; TemplateKey = 'fluid'; Shared = $true; Tags = @('fluid') },
    [PSCustomObject]@{ Code = 'PROD007'; Name = 'ワーク位置決めユニット'; Category = '治具'; Type = '標準品'; Phase = '設計'; Status = '承認待ち'; Owner = $internalUsers[0].DisplayName; Note = '複数案件で共通利用する位置決めモジュール。'; Drive = '手動調整'; Power = ''; Line = '共通モジュール'; Location = '加工点手前'; TemplateKey = 'locating'; Shared = $true; Tags = @('locating') },
    [PSCustomObject]@{ Code = 'PROD008'; Name = 'リフターユニット'; Category = '搬送装置'; Type = '標準品'; Phase = '設計'; Status = '設計中'; Owner = $internalUsers[1].DisplayName; Note = '上下搬送を担う共通モジュール。'; Drive = 'エアシリンダ'; Power = 'DC24V'; Line = '共通モジュール'; Location = '搬送昇降部'; TemplateKey = 'lifting'; Shared = $true; Tags = @('lifting') },
    [PSCustomObject]@{ Code = 'PROD009'; Name = 'ツーリングベースユニット'; Category = '治具'; Type = '標準品'; Phase = '設計'; Status = '承認待ち'; Owner = $internalUsers[2].DisplayName; Note = '交換式ツーリングのベースユニット。'; Drive = '手動交換'; Power = ''; Line = '共通モジュール'; Location = '加工点'; TemplateKey = 'tooling'; Shared = $true; Tags = @('tooling') },
    [PSCustomObject]@{ Code = 'PROD010'; Name = '部品供給ユニット'; Category = '搬送装置'; Type = '標準品'; Phase = '設計'; Status = '設計中'; Owner = $internalUsers[3].DisplayName; Note = '小物部品の供給を担う共通モジュール。'; Drive = '振動フィーダ'; Power = 'AC100V'; Line = '共通モジュール'; Location = '供給部'; TemplateKey = 'feeding'; Shared = $true; Tags = @('feeding') },
    [PSCustomObject]@{ Code = 'PROD011'; Name = 'EVモータケース洗浄セル'; Category = '加工機'; Type = '特注品'; Phase = '設計'; Status = '設計中'; Owner = $internalUsers[4].DisplayName; Note = 'モータケース洗浄の主設備。'; Drive = 'サーボモータ'; Power = 'AC200V'; Line = '洗浄ラインA'; Location = '洗浄工程'; TemplateKey = 'fluid'; Shared = $false; Tags = @('main','conveyor','fluid','locating') },
    [PSCustomObject]@{ Code = 'PROD012'; Name = 'シャフト自動計測セル'; Category = '検査装置'; Type = '特注品'; Phase = '設計'; Status = '設計中'; Owner = $internalUsers[5].DisplayName; Note = '小径シャフト計測の主設備。'; Drive = '電動スライダ'; Power = 'AC200V'; Line = '計測ラインB'; Location = '計測工程'; TemplateKey = 'inspection'; Shared = $false; Tags = @('main','inspection','locating','control') },
    [PSCustomObject]@{ Code = 'PROD013'; Name = 'バルブボディ外観検査セル'; Category = '検査装置'; Type = '特注品'; Phase = '設計'; Status = '設計中'; Owner = $internalUsers[0].DisplayName; Note = '外観検査と洗浄を組み合わせた主設備。'; Drive = 'インデックステーブル'; Power = 'AC200V'; Line = '検査ラインC'; Location = '検査工程'; TemplateKey = 'inspection'; Shared = $false; Tags = @('main','inspection','fluid') },
    [PSCustomObject]@{ Code = 'PROD014'; Name = '冷却プレート組立セル'; Category = '組立装置'; Type = '特注品'; Phase = '設計'; Status = '承認待ち'; Owner = $internalUsers[1].DisplayName; Note = '冷却プレート組立の主設備。'; Drive = 'サーボプレス'; Power = 'AC200V'; Line = '組立ラインD'; Location = '組立工程'; TemplateKey = 'tooling'; Shared = $false; Tags = @('main','tooling','feeding','locating') },
    [PSCustomObject]@{ Code = 'PROD015'; Name = 'ブレーキブラケット加工セル'; Category = '加工機'; Type = '特注品'; Phase = '製造・組立'; Status = '製作中'; Owner = $internalUsers[2].DisplayName; Note = '切削加工を行う主設備。'; Drive = 'サーボモータ'; Power = 'AC200V'; Line = '加工ラインE'; Location = '加工工程'; TemplateKey = 'fluid'; Shared = $false; Tags = @('main','conveyor','tooling','fluid') },
    [PSCustomObject]@{ Code = 'PROD016'; Name = 'バッテリケース漏れ検査設備'; Category = '検査装置'; Type = '特注品'; Phase = '設計'; Status = '承認待ち'; Owner = $internalUsers[3].DisplayName; Note = '漏れ検査を行う主設備。'; Drive = 'エア加圧'; Power = 'AC200V'; Line = '検査ラインF'; Location = '検査工程'; TemplateKey = 'inspection'; Shared = $false; Tags = @('main','inspection','fluid','safety') },
    [PSCustomObject]@{ Code = 'PROD017'; Name = 'シール圧入確認セル'; Category = '組立装置'; Type = '特注品'; Phase = '設計'; Status = '設計中'; Owner = $internalUsers[4].DisplayName; Note = '圧入と寸法確認を行う主設備。'; Drive = 'サーボプレス'; Power = 'AC200V'; Line = '組立ラインG'; Location = '圧入工程'; TemplateKey = 'feeding'; Shared = $false; Tags = @('main','feeding','locating','inspection') },
    [PSCustomObject]@{ Code = 'PROD018'; Name = 'ロータ搬送更新モジュール'; Category = '搬送装置'; Type = '特注品'; Phase = '製造・組立'; Status = '製作中'; Owner = $internalUsers[5].DisplayName; Note = '既設搬送更新向けの主モジュール。'; Drive = 'サーボモータ'; Power = 'AC200V'; Line = '搬送ラインH'; Location = '搬送工程'; TemplateKey = 'lifting'; Shared = $false; Tags = @('main','conveyor','lifting','tooling') },
    [PSCustomObject]@{ Code = 'PROD019'; Name = 'ハウジング反転搬送ユニット'; Category = '搬送装置'; Type = '特注品'; Phase = '設計'; Status = '設計中'; Owner = $internalUsers[0].DisplayName; Note = 'ワーク反転搬送を行う主ユニット。'; Drive = 'サーボモータ'; Power = 'AC200V'; Line = '搬送ラインI'; Location = '反転工程'; TemplateKey = 'lifting'; Shared = $false; Tags = @('main','conveyor','lifting','safety') },
    [PSCustomObject]@{ Code = 'PROD020'; Name = '出荷前最終検査セル'; Category = '検査装置'; Type = '特注品'; Phase = '設計'; Status = '承認待ち'; Owner = $internalUsers[1].DisplayName; Note = '出荷前検査を行う主設備。'; Drive = '電動スライダ'; Power = 'AC200V'; Line = '最終検査ラインJ'; Location = '最終検査工程'; TemplateKey = 'inspection'; Shared = $false; Tags = @('main','inspection','conveyor','control') }
)

$projectProductMap = @{
    'PRJ260601' = @('PROD011', 'PROD001', 'PROD002', 'PROD003', 'PROD006', 'PROD007')
    'PRJ260602' = @('PROD012', 'PROD001', 'PROD002', 'PROD004', 'PROD007')
    'PRJ260603' = @('PROD013', 'PROD001', 'PROD004', 'PROD005', 'PROD006')
    'PRJ260604' = @('PROD014', 'PROD001', 'PROD002', 'PROD009', 'PROD010')
    'PRJ260605' = @('PROD015', 'PROD001', 'PROD003', 'PROD006', 'PROD009')
    'PRJ260606' = @('PROD016', 'PROD001', 'PROD004', 'PROD005', 'PROD007')
    'PRJ260607' = @('PROD017', 'PROD001', 'PROD004', 'PROD007', 'PROD010')
    'PRJ260608' = @('PROD018', 'PROD001', 'PROD002', 'PROD003', 'PROD008')
    'PRJ260609' = @('PROD019', 'PROD001', 'PROD003', 'PROD008')
    'PRJ260610' = @('PROD020', 'PROD001', 'PROD002', 'PROD003', 'PROD004')
}

$productHierarchyMap = @{
    'PROD011' = @('PROD001', 'PROD002', 'PROD003', 'PROD006', 'PROD007')
    'PROD012' = @('PROD001', 'PROD002', 'PROD004', 'PROD007')
    'PROD013' = @('PROD001', 'PROD004', 'PROD005', 'PROD006')
    'PROD014' = @('PROD001', 'PROD002', 'PROD009', 'PROD010')
    'PROD015' = @('PROD001', 'PROD003', 'PROD006', 'PROD009')
    'PROD016' = @('PROD001', 'PROD004', 'PROD005', 'PROD007')
    'PROD017' = @('PROD001', 'PROD004', 'PROD007', 'PROD010')
    'PROD018' = @('PROD001', 'PROD002', 'PROD003', 'PROD008')
    'PROD019' = @('PROD001', 'PROD003', 'PROD008')
    'PROD020' = @('PROD001', 'PROD002', 'PROD003', 'PROD004')
}

$sharedPartBlueprints = @(
    [PSCustomObject]@{ Number = 'STD-FAST-001'; Name = '六角穴付ボルト M6x20'; Category = '締結部品'; Status = '使用中'; Material = 'SCM435'; Surface = '三価クロメート'; Environment = '一般屋内'; Importance = 'A'; Groups = @('all'); Note = '共通締結部品' },
    [PSCustomObject]@{ Number = 'STD-FAST-002'; Name = '六角穴付ボルト M8x25'; Category = '締結部品'; Status = '使用中'; Material = 'SCM435'; Surface = '三価クロメート'; Environment = '一般屋内'; Importance = 'A'; Groups = @('all'); Note = '共通締結部品' },
    [PSCustomObject]@{ Number = 'STD-FAST-003'; Name = '平ワッシャー M6'; Category = '締結部品'; Status = '使用中'; Material = 'SUS304'; Surface = ''; Environment = '一般屋内'; Importance = 'B'; Groups = @('all'); Note = '共通締結部品' },
    [PSCustomObject]@{ Number = 'STD-FAST-004'; Name = '平ワッシャー M8'; Category = '締結部品'; Status = '使用中'; Material = 'SUS304'; Surface = ''; Environment = '一般屋内'; Importance = 'B'; Groups = @('all'); Note = '共通締結部品' },
    [PSCustomObject]@{ Number = 'STD-FAST-005'; Name = 'フランジナット M6'; Category = '締結部品'; Status = '使用中'; Material = 'SCM435'; Surface = '三価クロメート'; Environment = '一般屋内'; Importance = 'B'; Groups = @('all'); Note = '共通締結部品' },
    [PSCustomObject]@{ Number = 'STD-FAST-006'; Name = 'フランジナット M8'; Category = '締結部品'; Status = '使用中'; Material = 'SCM435'; Surface = '三価クロメート'; Environment = '一般屋内'; Importance = 'B'; Groups = @('all'); Note = '共通締結部品' },
    [PSCustomObject]@{ Number = 'STD-DRV-001'; Name = 'タイミングプーリ 32T'; Category = '駆動部品'; Status = '量産'; Material = 'S45C'; Surface = '黒染め'; Environment = '一般屋内'; Importance = 'A'; Groups = @('conveyor', 'lifting'); Note = '共通駆動部品' },
    [PSCustomObject]@{ Number = 'STD-DRV-002'; Name = 'タイミングベルト 840-8M'; Category = '駆動部品'; Status = '量産'; Material = 'ゴム'; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('conveyor', 'lifting'); Note = '共通駆動部品' },
    [PSCustomObject]@{ Number = 'STD-DRV-003'; Name = 'サーボモータ 200W'; Category = '駆動部品'; Status = '使用中'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('conveyor', 'inspection', 'control'); Note = '共通駆動部品' },
    [PSCustomObject]@{ Number = 'STD-DRV-004'; Name = 'カップリング 14-14'; Category = '駆動部品'; Status = '使用中'; Material = 'S45C'; Surface = '黒染め'; Environment = '一般屋内'; Importance = 'B'; Groups = @('conveyor', 'lifting'); Note = '共通駆動部品' },
    [PSCustomObject]@{ Number = 'STD-DRV-005'; Name = 'リニアブッシュ LM20UU'; Category = '駆動部品'; Status = '使用中'; Material = 'SUJ2'; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('locating', 'inspection', 'lifting'); Note = '共通駆動部品' },
    [PSCustomObject]@{ Number = 'STD-CNV-001'; Name = 'パレットストッパ ASSY'; Category = '搬送部品'; Status = '承認済み'; Material = 'S45C'; Surface = '黒染め'; Environment = '一般屋内'; Importance = 'A'; Groups = @('conveyor', 'feeding'); Note = '共通搬送部品' },
    [PSCustomObject]@{ Number = 'STD-CNV-002'; Name = 'サイドガイド 300L'; Category = '搬送部品'; Status = '承認済み'; Material = 'A6063'; Surface = 'アルマイト'; Environment = '一般屋内'; Importance = 'B'; Groups = @('conveyor', 'feeding'); Note = '共通搬送部品' },
    [PSCustomObject]@{ Number = 'STD-CNV-003'; Name = 'ベルトガイド UHMW'; Category = '搬送部品'; Status = '承認済み'; Material = 'UHMW-PE'; Surface = ''; Environment = '一般屋内'; Importance = 'B'; Groups = @('conveyor'); Note = '共通搬送部品' },
    [PSCustomObject]@{ Number = 'STD-CNV-004'; Name = 'フロートプレート'; Category = '搬送部品'; Status = '設計中'; Material = 'SUS304'; Surface = ''; Environment = '一般屋内'; Importance = 'B'; Groups = @('lifting', 'conveyor'); Note = '共通搬送部品' },
    [PSCustomObject]@{ Number = 'STD-CNV-005'; Name = 'ケーブルベア 25x50'; Category = '搬送部品'; Status = '使用中'; Material = '樹脂'; Surface = ''; Environment = '一般屋内'; Importance = 'B'; Groups = @('conveyor', 'lifting', 'inspection'); Note = '共通搬送部品' },
    [PSCustomObject]@{ Number = 'STD-SNS-001'; Name = '近接センサ M12'; Category = 'センサ部品'; Status = '使用中'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('inspection', 'locating', 'safety'); Note = '共通センサ部品' },
    [PSCustomObject]@{ Number = 'STD-SNS-002'; Name = 'フォトセンサ アンプ内蔵'; Category = 'センサ部品'; Status = '使用中'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('inspection', 'feeding'); Note = '共通センサ部品' },
    [PSCustomObject]@{ Number = 'STD-SNS-003'; Name = 'リードスイッチ 2線式'; Category = 'センサ部品'; Status = '使用中'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'B'; Groups = @('lifting', 'safety'); Note = '共通センサ部品' },
    [PSCustomObject]@{ Number = 'STD-SNS-004'; Name = '画像照明リング 24V'; Category = 'センサ部品'; Status = '承認済み'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('inspection'); Note = '共通センサ部品' },
    [PSCustomObject]@{ Number = 'STD-SNS-005'; Name = '原点センサブラケット'; Category = 'センサ部品'; Status = '承認済み'; Material = 'A5052'; Surface = 'アルマイト'; Environment = '一般屋内'; Importance = 'B'; Groups = @('inspection', 'locating', 'conveyor'); Note = '共通センサ部品' },
    [PSCustomObject]@{ Number = 'STD-CTL-001'; Name = 'PLCユニットベース'; Category = '制御部品'; Status = '承認済み'; Material = 'SPCC'; Surface = '亜鉛メッキ'; Environment = '一般屋内'; Importance = 'A'; Groups = @('control'); Note = '共通制御部品' },
    [PSCustomObject]@{ Number = 'STD-CTL-002'; Name = '端子台 20極'; Category = '制御部品'; Status = '使用中'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('control'); Note = '共通制御部品' },
    [PSCustomObject]@{ Number = 'STD-CTL-003'; Name = '配線ダクト 60x40'; Category = '制御部品'; Status = '使用中'; Material = 'PVC'; Surface = ''; Environment = '一般屋内'; Importance = 'B'; Groups = @('control'); Note = '共通制御部品' },
    [PSCustomObject]@{ Number = 'STD-CTL-004'; Name = '電源ユニット 24V 10A'; Category = '制御部品'; Status = '使用中'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('control', 'inspection'); Note = '共通制御部品' },
    [PSCustomObject]@{ Number = 'STD-NZL-001'; Name = 'ノズルチップ φ1.2'; Category = 'ノズル部品'; Status = '試作'; Material = 'SUS303'; Surface = '電解研磨'; Environment = '水・クーラント'; Importance = 'A'; Groups = @('fluid'); Note = '共通ノズル部品' },
    [PSCustomObject]@{ Number = 'STD-NZL-002'; Name = 'ノズルチップ φ2.0'; Category = 'ノズル部品'; Status = '試作'; Material = 'SUS303'; Surface = '電解研磨'; Environment = '水・クーラント'; Importance = 'A'; Groups = @('fluid'); Note = '共通ノズル部品' },
    [PSCustomObject]@{ Number = 'STD-NZL-003'; Name = 'スプレーヘッダ 4連'; Category = 'ノズル部品'; Status = '設計中'; Material = 'SUS304'; Surface = ''; Environment = '水・クーラント'; Importance = 'A'; Groups = @('fluid'); Note = '共通ノズル部品' },
    [PSCustomObject]@{ Number = 'STD-FLD-001'; Name = 'エアレギュレータ Rc1/4'; Category = '流体部品'; Status = '使用中'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('fluid', 'lifting', 'feeding'); Note = '共通流体部品' },
    [PSCustomObject]@{ Number = 'STD-FLD-002'; Name = 'クイック継手 φ8'; Category = '流体部品'; Status = '使用中'; Material = '黄銅'; Surface = 'ニッケルメッキ'; Environment = '一般屋内'; Importance = 'B'; Groups = @('fluid', 'lifting', 'feeding'); Note = '共通流体部品' },
    [PSCustomObject]@{ Number = 'STD-SAF-001'; Name = '非常停止スイッチ 30径'; Category = '安全部品'; Status = '使用中'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('safety', 'control'); Note = '共通安全部品' },
    [PSCustomObject]@{ Number = 'STD-SAF-002'; Name = 'ドアスイッチ マグネット式'; Category = '安全部品'; Status = '承認済み'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'A'; Groups = @('safety'); Note = '共通安全部品' },
    [PSCustomObject]@{ Number = 'STD-SAF-003'; Name = '警告灯 3段'; Category = '安全部品'; Status = '使用中'; Material = ''; Surface = ''; Environment = '一般屋内'; Importance = 'B'; Groups = @('safety', 'control'); Note = '共通安全部品' },
    [PSCustomObject]@{ Number = 'STD-PLT-001'; Name = 'アルミフレーム 40x40'; Category = '板金部品'; Status = '使用中'; Material = 'A6063'; Surface = 'アルマイト'; Environment = '一般屋内'; Importance = 'A'; Groups = @('all'); Note = '共通構造部品' },
    [PSCustomObject]@{ Number = 'STD-PLT-002'; Name = 'ポリカーボネート窓板 t5'; Category = '板金部品'; Status = '承認済み'; Material = 'PC'; Surface = ''; Environment = '一般屋内'; Importance = 'B'; Groups = @('safety', 'inspection'); Note = '共通構造部品' },
    [PSCustomObject]@{ Number = 'STD-PLT-003'; Name = '取付ベースプレート 250x180'; Category = '板金部品'; Status = '使用中'; Material = 'SS400'; Surface = '粉体塗装'; Environment = '一般屋内'; Importance = 'B'; Groups = @('all'); Note = '共通構造部品' },
    [PSCustomObject]@{ Number = 'STD-PLT-004'; Name = '支柱ブラケット 90角'; Category = '板金部品'; Status = '使用中'; Material = 'SS400'; Surface = '粉体塗装'; Environment = '一般屋内'; Importance = 'B'; Groups = @('all'); Note = '共通構造部品' },
    [PSCustomObject]@{ Number = 'STD-ELC-001'; Name = 'ケーブルクランプ 20A'; Category = '電装部品'; Status = '使用中'; Material = 'PA66'; Surface = ''; Environment = '一般屋内'; Importance = 'C'; Groups = @('control', 'inspection', 'feeding'); Note = '共通電装部品' },
    [PSCustomObject]@{ Number = 'STD-ELC-002'; Name = 'ケーブルグランド M20'; Category = '電装部品'; Status = '使用中'; Material = '黄銅'; Surface = 'ニッケルメッキ'; Environment = '一般屋内'; Importance = 'C'; Groups = @('control'); Note = '共通電装部品' },
    [PSCustomObject]@{ Number = 'STD-ELC-003'; Name = 'アースバー 10極'; Category = '電装部品'; Status = '承認済み'; Material = '銅'; Surface = 'スズメッキ'; Environment = '一般屋内'; Importance = 'B'; Groups = @('control'); Note = '共通電装部品' }
)

$parts = New-Object System.Collections.Generic.List[object]
$partRowsByNumber = @{}

foreach ($blueprint in $sharedPartBlueprints) {
    $supplierName = switch -Wildcard ($blueprint.Number) {
        'STD-FAST-*' { '共栄ファスナー株式会社'; break }
        'STD-DRV-*'  { '日東駆動部品株式会社'; break }
        'STD-CNV-*'  { '新生搬送機器株式会社'; break }
        'STD-SNS-*'  { '光和センサテック株式会社'; break }
        'STD-CTL-*'  { '瑞光制御機器株式会社'; break }
        'STD-NZL-*'  { '東洋流体機器株式会社'; break }
        'STD-FLD-*'  { '東洋流体機器株式会社'; break }
        'STD-SAF-*'  { '双葉安全機材株式会社'; break }
        'STD-PLT-*'  { '三晴金属工業株式会社'; break }
        'STD-ELC-*'  { '瑞光制御機器株式会社'; break }
        default      { '' }
    }
    $unitPrice = switch -Wildcard ($blueprint.Number) {
        'STD-FAST-001' { '18' ; break }
        'STD-FAST-002' { '24' ; break }
        'STD-FAST-003' { '6' ; break }
        'STD-FAST-004' { '8' ; break }
        'STD-FAST-005' { '14' ; break }
        'STD-FAST-006' { '17' ; break }
        'STD-DRV-*'    { '6800' ; break }
        'STD-CNV-*'    { '4200' ; break }
        'STD-SNS-*'    { '9800' ; break }
        'STD-CTL-*'    { '12500' ; break }
        'STD-NZL-*'    { '3800' ; break }
        'STD-FLD-*'    { '2100' ; break }
        'STD-SAF-*'    { '7600' ; break }
        'STD-PLT-*'    { '5600' ; break }
        'STD-ELC-*'    { '1200' ; break }
        default        { '' }
    }
    $row = New-OrderedObject @{
        '部品番号'   = $blueprint.Number
        '部品名'     = $blueprint.Name
        'カテゴリ'   = $blueprint.Category
        'ステータス' = $blueprint.Status
        '仕入先'     = $supplierName
        '単価'       = $unitPrice
        '単位'       = '個'
        '担当者'     = ''
        '備考'       = $blueprint.Note
        '材質'       = $blueprint.Material
        '表面処理'   = $blueprint.Surface
        '使用環境'   = $blueprint.Environment
        '重要度'     = $blueprint.Importance
    }
    $parts.Add($row)
    $partRowsByNumber[$blueprint.Number] = $row
}

$partStatusCycle = @('設計中', 'レビュー待ち', '承認待ち', '承認済み', '試作', '使用中')
$productSpecificPartLinks = New-Object System.Collections.Generic.List[object]
$partCounter = 1

foreach ($product in $products) {
    $templates = Get-ProductPartTemplates -TemplateKey $product.TemplateKey
    $index = 1
    foreach ($template in $templates) {
        $partNumber = ('PRT-{0}-{1:D3}' -f $product.Code.Replace('PROD', ''), $index)
        $status = $partStatusCycle[($partCounter - 1) % $partStatusCycle.Count]
        $row = New-OrderedObject @{
            '部品番号'   = $partNumber
            '部品名'     = ('{0} {1}' -f $product.Name, $template.Suffix)
            'カテゴリ'   = $template.Category
            'ステータス' = $status
            '仕入先'     = '内製'
            '単価'       = ''
            '単位'       = '個'
            '担当者'     = $product.Owner
            '備考'       = ('{0} 向け専用部品' -f $product.Name)
            '材質'       = $template.Material
            '表面処理'   = $template.Surface
            '使用環境'   = $template.Environment
            '重要度'     = $template.Importance
        }
        $parts.Add($row)
        $partRowsByNumber[$partNumber] = $row
        $productSpecificPartLinks.Add([PSCustomObject]@{
            ProductCode = $product.Code
            PartNumber  = $partNumber
            Quantity    = 1
            Note        = ('{0} 専用部品' -f $product.Name)
        })
        $index += 1
        $partCounter += 1
    }
}

$productPartLinks = New-Object System.Collections.Generic.List[object]

foreach ($link in $productSpecificPartLinks) {
    $productPartLinks.Add($link)
}

foreach ($blueprint in $sharedPartBlueprints) {
    foreach ($product in $products) {
        $matches = $false
        if ($blueprint.Groups -contains 'all') {
            $matches = $true
        }
        else {
            foreach ($group in $blueprint.Groups) {
                if ($product.Tags -contains $group) {
                    $matches = $true
                    break
                }
            }
        }

        if ($matches) {
            $productPartLinks.Add([PSCustomObject]@{
                ProductCode = $product.Code
                PartNumber  = $blueprint.Number
                Quantity    = 1
                Note        = '共通標準部品'
            })
        }
    }
}

$drawingRows = New-Object System.Collections.Generic.List[object]
$drawingLinksProduct = New-Object System.Collections.Generic.List[object]
$drawingLinksPart = New-Object System.Collections.Generic.List[object]

foreach ($product in $products) {
    $drawingNumber = ('DRW-{0}-ASM-01' -f $product.Code.Replace('PROD', ''))
    $drawingType = if ($product.Shared) { '組立図' } else { 'レイアウト図' }
    $paperSize = if ($product.Shared) { 'A2' } else { 'A0' }
    $drawingRows.Add((New-OrderedObject @{
        '図面番号'       = $drawingNumber
        'タイトル'       = ('{0} 組立図' -f $product.Name)
        '図面タイプ'     = $drawingType
        '用紙サイズ'     = $paperSize
        '所有者'         = $product.Owner
        '備考'           = '展示会向け創作データ'
        '設計意図・目的' = ('{0} の構成と取合いを確認するための図面' -f $product.Name)
        'タグ'           = (($product.Tags | Where-Object { $PSItem -ne 'main' }) -join ';')
        '元ファイルパス' = ''
    }))
    $drawingLinksProduct.Add([PSCustomObject]@{
        ProductCode    = $product.Code
        DrawingNumber  = $drawingNumber
        Quantity       = 1
        Note           = '製品代表図面'
    })
}

$partDrawingCandidates = $parts | Select-Object -First 40
$partDrawingIndex = 1
foreach ($part in $partDrawingCandidates) {
    $drawingNumber = ('DRW-{0:D3}-PRT-01' -f $partDrawingIndex)
    $drawingRows.Add((New-OrderedObject @{
        '図面番号'       = $drawingNumber
        'タイトル'       = ('{0} 部品図' -f $part.'部品名')
        '図面タイプ'     = '部品図'
        '用紙サイズ'     = 'A3'
        '所有者'         = $part.'担当者'
        '備考'           = '展示会向け創作データ'
        '設計意図・目的' = ('{0} の単品加工・手配に使用する部品図' -f $part.'部品名')
        'タグ'           = $part.'カテゴリ'
        '元ファイルパス' = ''
    }))
    $drawingLinksPart.Add([PSCustomObject]@{
        PartNumber     = $part.'部品番号'
        DrawingNumber  = $drawingNumber
        Quantity       = 1
        Note           = '部品図'
    })
    $partDrawingIndex += 1
}

$documentRows = New-Object System.Collections.Generic.List[object]
$documentLinksProject = New-Object System.Collections.Generic.List[object]
$documentLinksProduct = New-Object System.Collections.Generic.List[object]
$documentLinksPart = New-Object System.Collections.Generic.List[object]

foreach ($project in $projects) {
    foreach ($docDef in @(
        [PSCustomObject]@{ Suffix = '要件仕様書'; Type = '仕様書'; Status = '承認済み'; Note = '設備要求を整理した仕様書' },
        [PSCustomObject]@{ Suffix = 'レイアウト検討書'; Type = '設計書'; Status = 'レビュー中'; Note = '設備配置案を整理した設計書' },
        [PSCustomObject]@{ Suffix = '運転手順書'; Type = 'マニュアル'; Status = '承認待ち'; Note = 'デモ説明に使える運転手順書' }
    )) {
        $title = ('{0}_{1}' -f $project.Code, $docDef.Suffix)
        $documentRows.Add((New-OrderedObject @{
            'タイトル'       = $title
            '文書タイプ'     = $docDef.Type
            'ステータス'     = $docDef.Status
            '所有者'         = $project.Manager
            '備考'           = '展示会向け創作データ'
            'タグ'           = '展示会デモ;創作案件'
            '元ファイルパス' = ''
            '文書概要'       = $docDef.Note
        }))
        $documentLinksProject.Add([PSCustomObject]@{
            ProjectCode   = $project.Code
            DocumentTitle = $title
            Quantity      = 1
            Note          = $docDef.Note
        })
    }
}

foreach ($product in $products) {
    $docType = if ($product.Shared) { 'マニュアル' } else { '設計書' }
    $docStatus = if ($product.Shared) { '承認済み' } else { 'レビュー中' }
    $docSuffix = if ($product.Shared) { '保守点検手順書' } else { '構想設計書' }
    $title = ('{0}_{1}' -f $product.Code, $docSuffix)
    $documentRows.Add((New-OrderedObject @{
        'タイトル'       = $title
        '文書タイプ'     = $docType
        'ステータス'     = $docStatus
        '所有者'         = $product.Owner
        '備考'           = '展示会向け創作データ'
        'タグ'           = '展示会デモ;製品文書'
        '元ファイルパス' = ''
        '文書概要'       = ('{0} に関する説明文書' -f $product.Name)
    }))
    $documentLinksProduct.Add([PSCustomObject]@{
        ProductCode    = $product.Code
        DocumentTitle  = $title
        Quantity       = 1
        Note           = '製品関連文書'
    })
}

$projectLookup = @{}
foreach ($project in $projects) { $projectLookup[$project.Code] = $project }
$productLookup = @{}
foreach ($product in $products) { $productLookup[$product.Code] = $product }

$projectProductRows = New-Object System.Collections.Generic.List[object]
foreach ($project in $projects) {
    foreach ($productCode in $projectProductMap[$project.Code]) {
        $projectProductRows.Add((New-OrderedObject @{
            'プロジェクト名'               = $project.Name
            '製品・装置・ユニット名'       = $productLookup[$productCode].Name
            '数量'                         = 1
            '備考'                         = if ($productLookup[$productCode].Shared) { '共通モジュール' } else { '案件主構成' }
        }))
    }
}

$productHierarchyRows = New-Object System.Collections.Generic.List[object]
foreach ($parentCode in $productHierarchyMap.Keys) {
    foreach ($childCode in $productHierarchyMap[$parentCode]) {
        $productHierarchyRows.Add((New-OrderedObject @{
            '親製品・装置・ユニット名' = $productLookup[$parentCode].Name
            '子製品・装置・ユニット名' = $productLookup[$childCode].Name
            '数量'                     = 1
            '備考'                     = '共通モジュールを子要素として利用'
        }))
    }
}

$productPartRows = New-Object System.Collections.Generic.List[object]
foreach ($link in $productPartLinks) {
    $productPartRows.Add((New-OrderedObject @{
        '製品・装置・ユニット名' = $productLookup[$link.ProductCode].Name
        '部品番号'               = $link.PartNumber
        '数量'                   = $link.Quantity
        '備考'                   = $link.Note
    }))
}

$productDrawRows = New-Object System.Collections.Generic.List[object]
foreach ($link in $drawingLinksProduct) {
    $productDrawRows.Add((New-OrderedObject @{
        '製品・装置・ユニット名' = $productLookup[$link.ProductCode].Name
        '図面番号'               = $link.DrawingNumber
        '数量'                   = $link.Quantity
        '備考'                   = $link.Note
    }))
}

$partDrawRows = New-Object System.Collections.Generic.List[object]
foreach ($link in $drawingLinksPart) {
    $partDrawRows.Add((New-OrderedObject @{
        '部品番号' = $link.PartNumber
        '図面番号' = $link.DrawingNumber
        '数量'     = $link.Quantity
        '備考'     = $link.Note
    }))
}

$projectDrawingRows = New-Object System.Collections.Generic.List[object]
foreach ($project in $projects) {
    $productCodes = $projectProductMap[$project.Code]
    $drawingNumbers = New-Object System.Collections.Generic.HashSet[string]

    foreach ($productCode in $productCodes) {
        foreach ($drawLink in $drawingLinksProduct | Where-Object { $PSItem.ProductCode -eq $productCode }) {
            [void]$drawingNumbers.Add($drawLink.DrawingNumber)
        }

        foreach ($partLink in $productPartLinks | Where-Object { $PSItem.ProductCode -eq $productCode }) {
            foreach ($drawLink in $drawingLinksPart | Where-Object { $PSItem.PartNumber -eq $partLink.PartNumber }) {
                [void]$drawingNumbers.Add($drawLink.DrawingNumber)
            }
        }
    }

    foreach ($drawingNumber in $drawingNumbers) {
        $projectDrawingRows.Add((New-OrderedObject @{
            'プロジェクト名' = $project.Name
            '図面番号'       = $drawingNumber
            '数量'           = 1
            '備考'           = 'プロジェクトに紐づく図面'
        }))
    }
}

$projectDocumentRows = New-Object System.Collections.Generic.List[object]
foreach ($link in $documentLinksProject) {
    $projectDocumentRows.Add((New-OrderedObject @{
        'プロジェクト名' = $projectLookup[$link.ProjectCode].Name
        '文書名'         = $link.DocumentTitle
        '数量'           = $link.Quantity
        '備考'           = $link.Note
    }))
}

foreach ($project in $projects) {
    foreach ($productCode in $projectProductMap[$project.Code]) {
        foreach ($docLink in $documentLinksProduct | Where-Object { $PSItem.ProductCode -eq $productCode }) {
            $projectDocumentRows.Add((New-OrderedObject @{
                'プロジェクト名' = $project.Name
                '文書名'         = $docLink.DocumentTitle
                '数量'           = 1
                '備考'           = '共通製品に紐づく文書'
            }))
        }
    }
}

$productDocumentRows = New-Object System.Collections.Generic.List[object]
foreach ($docLink in $documentLinksProduct) {
    $productDocumentRows.Add((New-OrderedObject @{
        '製品・装置・ユニット名' = $productLookup[$docLink.ProductCode].Name
        '文書名'                 = $docLink.DocumentTitle
        '数量'                   = $docLink.Quantity
        '備考'                   = $docLink.Note
    }))
}

$partDocumentRows = New-Object System.Collections.Generic.List[object]
foreach ($link in $productSpecificPartLinks) {
    $productDoc = $documentLinksProduct | Where-Object { $PSItem.ProductCode -eq $link.ProductCode } | Select-Object -First 1
    if ($null -ne $productDoc) {
        $partDocumentRows.Add((New-OrderedObject @{
            '部品番号' = $link.PartNumber
            '文書名'   = $productDoc.DocumentTitle
            '数量'     = 1
            '備考'     = '所属製品の関連文書'
        }))
    }
}

$customerRows = foreach ($customer in $customers) {
    New-OrderedObject @{
        '顧客名'   = $customer.CustomerName
        '会社名'   = $customer.CompanyName
        '部署'     = $customer.Department
        '備考'     = '展示会向け創作顧客'
    }
}

$contactRows = foreach ($customer in $customers) {
    New-OrderedObject @{
        '顧客名'         = $customer.CustomerName
        '顧客担当者'     = $customer.ContactDisplayName
        '姓'             = $customer.ContactLastName
        '名'             = $customer.ContactFirstName
        'メールアドレス' = $customer.ContactEmail
        '部署'           = $customer.Department
        '役職'           = $customer.ContactTitle
        '備考'           = '展示会向け創作顧客担当者'
    }
}

$internalUserRows = foreach ($user in $internalUsers) {
    New-OrderedObject @{
        'ユーザー名'     = $user.DisplayName
        '姓'             = $user.LastName
        '名'             = $user.FirstName
        'メールアドレス' = $user.Email
        '会社名'         = $internalCompanyName
        '部署'           = $user.Department
        '役職'           = $user.Title
        '備考'           = '展示会向け創作ユーザー'
    }
}

$partCategoryRows = foreach ($category in $partCategories) {
    New-OrderedObject @{
        'カテゴリ名' = $category
        '備考'       = '展示会向け創作部品カテゴリ'
    }
}

$projectRows = foreach ($project in $projects) {
    New-OrderedObject @{
        'プロジェクト名' = $project.Name
        '顧客名'         = $project.Customer
        '顧客担当者'     = $project.Contact
        'ステータス'     = $project.Status
        '責任者'         = $project.Manager
        '開始日'         = $project.Start
        '終了予定日'     = $project.PlannedEnd
        '終了日'         = $project.End
        '備考'           = $project.Note
    }
}

$productRows = foreach ($product in $products) {
    New-OrderedObject @{
        '製品・装置・ユニット名' = $product.Name
        'カテゴリ'               = $product.Category
        '種別'                   = $product.Type
        'フェーズ'               = $product.Phase
        'ステータス'             = $product.Status
        '担当者'                 = $product.Owner
        '備考'                   = $product.Note
        '駆動方式'               = $product.Drive
        '電源'                   = $product.Power
        'ライン名'               = $product.Line
        '設置場所'               = $product.Location
    }
}

$partRows = $parts
$drawingRowsExport = $drawingRows
$documentRowsExport = $documentRows

$readme = @(
    '# 展示会向け PDM CSVセット',
    '',
    '## 目的',
    '',
    '- 展示会デモで使えるように、実在しないが自然な名称で統一した PDM 登録用 CSV をまとめる。',
    '- 会社名、人名、案件名、製品、部品、図面、文書はすべて創作データ。',
    '- 客先は同一企業の別部署を含む構成にしている。',
    '- 異なるプロジェクトで共通製品を流用し、共通部品も複数製品で使い回す構成にしている。',
    '- 部品は購入品と内製品を混在させ、`仕入先` と `単位` の見え方も付けている。',
    '',
    '## 件数',
    '',
    '- 顧客: 10',
    '- 顧客担当者: 10',
    '- ユーザー: 6',
    '- プロジェクト: 10',
    '- 製品・装置・ユニット: 20',
    '- 部品: 200',
    '- 図面: 60',
    '- 文書: 50',
    '',
    '## データ設計',
    '',
    '- `安全囲いユニット`、`制御盤ユニット`、`搬送コンベアユニット` などを共通製品として複数案件へ流用する。',
    '- `STD-FAST-*` や `STD-SNS-*` などの標準部品を複数製品で共通利用する。',
    '- 図面と文書は、製品・部品・プロジェクトへ紐づけ可能な形で分割している。',
    '- 実ファイル連携は不要の前提なので、`元ファイルパス` は空欄。',
    '- ユーザーは実画面の指摘に合わせて、`姓`、`名`、`メールアドレス`、`部署`、`役職` を持たせている。',
    '- 顧客担当者も基本的に `姓` と `名` を分割し、連絡先列を持たせている。',
    '',
    '## 主なファイル',
    '',
    '- `01_顧客.csv`',
    '- `02_顧客担当者.csv`',
    '- `03_ユーザー.csv`',
    '- `04_部品カテゴリマスタ.csv`',
    '- `05_プロジェクト.csv`',
    '- `06_製品・装置・ユニット.csv`',
    '- `07_部品.csv`',
    '- `08_図面.csv`',
    '- `09_文書.csv`',
    '- `10_プロジェクト_製品紐づけ.csv`',
    '- `11_製品_親子紐づけ.csv`',
    '- `12_製品_部品紐づけ.csv`',
    '- `13_プロジェクト_図面紐づけ.csv`',
    '- `14_製品_図面紐づけ.csv`',
    '- `15_部品_図面紐づけ.csv`',
    '- `16_プロジェクト_文書紐づけ.csv`',
    '- `17_製品_文書紐づけ.csv`',
    '- `18_部品_文書紐づけ.csv`'
) -join "`r`n"

if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$outputParentDir = Split-Path -Parent $OutputDir

Set-Content -LiteralPath (Join-Path $OutputDir '00_README.md') -Value $readme -Encoding utf8
if ($outputParentDir -and ($outputParentDir -ne $OutputDir)) {
    Set-Content -LiteralPath (Join-Path $outputParentDir '00_README.md') -Value $readme -Encoding utf8
}

Write-Utf8Csv -Path (Join-Path $OutputDir '01_顧客.csv') -Rows $customerRows
Write-Utf8Csv -Path (Join-Path $OutputDir '02_顧客担当者.csv') -Rows $contactRows
Write-Utf8Csv -Path (Join-Path $OutputDir '03_ユーザー.csv') -Rows $internalUserRows
Write-Utf8Csv -Path (Join-Path $OutputDir '04_部品カテゴリマスタ.csv') -Rows $partCategoryRows
Write-Utf8Csv -Path (Join-Path $OutputDir '05_プロジェクト.csv') -Rows $projectRows
Write-Utf8Csv -Path (Join-Path $OutputDir '06_製品・装置・ユニット.csv') -Rows $productRows
Write-Utf8Csv -Path (Join-Path $OutputDir '07_部品.csv') -Rows $partRows
Write-Utf8Csv -Path (Join-Path $OutputDir '08_図面.csv') -Rows $drawingRowsExport
Write-Utf8Csv -Path (Join-Path $OutputDir '09_文書.csv') -Rows $documentRowsExport
Write-Utf8Csv -Path (Join-Path $OutputDir '10_プロジェクト_製品紐づけ.csv') -Rows $projectProductRows
Write-Utf8Csv -Path (Join-Path $OutputDir '11_製品_親子紐づけ.csv') -Rows $productHierarchyRows
Write-Utf8Csv -Path (Join-Path $OutputDir '12_製品_部品紐づけ.csv') -Rows $productPartRows
Write-Utf8Csv -Path (Join-Path $OutputDir '13_プロジェクト_図面紐づけ.csv') -Rows $projectDrawingRows
Write-Utf8Csv -Path (Join-Path $OutputDir '14_製品_図面紐づけ.csv') -Rows $productDrawRows
Write-Utf8Csv -Path (Join-Path $OutputDir '15_部品_図面紐づけ.csv') -Rows $partDrawRows
Write-Utf8Csv -Path (Join-Path $OutputDir '16_プロジェクト_文書紐づけ.csv') -Rows $projectDocumentRows
Write-Utf8Csv -Path (Join-Path $OutputDir '17_製品_文書紐づけ.csv') -Rows $productDocumentRows
Write-Utf8Csv -Path (Join-Path $OutputDir '18_部品_文書紐づけ.csv') -Rows $partDocumentRows

if ($outputParentDir -and ($outputParentDir -ne $OutputDir)) {
    $zipPath = Join-Path $outputParentDir ((Split-Path -Leaf $OutputDir) + '.zip')
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -LiteralPath $OutputDir -DestinationPath $zipPath -Force
}

Write-Host "Generated exhibition PDM CSV set at: $OutputDir"
