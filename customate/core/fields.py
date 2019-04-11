from enumfields import Enum
from customate.settings import COUNTRIES_AVAILABLE
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from rest_framework_json_api.serializers import ChoiceField, UUIDField as DefaultUUIDField
from rest_framework_json_api.relations import ResourceRelatedField


class ResourceRelatedField(ResourceRelatedField):

    def use_pk_only_optimization(self):
        # TODO workaround
        #  Original exception text was: 'PKOnlyObject' object has no attribute 'address'.
        return False


class PrimitiveValueFieldMixin:

    def __init__(self, primitive_value=False, *args, **kwargs):
        self.primitive_value = primitive_value
        super().__init__(*args, **kwargs)

    def _prepare_internal_value(self, data):
        primitive_value = getattr(self, 'primitive_value', None)
        return data if not primitive_value else str(data)


class ResultResourceFieldMixin:

    def __init__(self, result_source=None, *args, **kwargs):
        if result_source:
            self.result_source = result_source

        return super().__init__(*args, **kwargs)


class UUIDField(PrimitiveValueFieldMixin, DefaultUUIDField):

    def to_internal_value(self, data):
        return self._prepare_internal_value(super().to_internal_value(data))


class EnumField(ResultResourceFieldMixin, PrimitiveValueFieldMixin, ChoiceField):
    def __init__(self, enum, value_field='value', *args, **kwargs):
        self.enum = enum
        self.value_field = value_field
        kwargs['choices'] = [(e.name, getattr(e, value_field)) for e in enum]
        super().__init__(*args, **kwargs)

    def to_representation(self, obj):
        return obj if isinstance(obj, str) else getattr(obj, self.value_field)

    def to_internal_value(self, data):
        try:
            return self._prepare_internal_value(self.enum[data])
        except KeyError:
            self.fail('invalid_choice', input=data)


class SerializerField(serializers.Field):

    def __init__(self, resource, many=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._resource = resource
        self._many = many

    def to_representation(self, instance):
        return self._resource(context=self.context, instance=instance, partial=True, many=self._many).to_representation(instance)

    def to_internal_value(self, data):
        instance = getattr(self.parent.instance, self.field_name)
        serializer = self._resource(instance=instance, context=self.context, data=data, partial=True, many=self._many)
        try:
            validated_data = serializer.to_internal_value(data)
            return validated_data
        except ValidationError as ex:
            errors = self._prepare_serializer_errors(ex)
            raise ValidationError(errors)

    @staticmethod
    def _prepare_serializer_errors(ex):

        detail = ex.detail
        if isinstance(detail, dict):
            errors = []
            for (key, value) in detail.items():
                value = value[0] if isinstance(value, list) else value
                errors.append({key: value})

            return errors

        return detail


class FeeType(Enum):
    STATIC = 'STATIC'
    PERCENTAGE = 'PERCENTAGE'

    class Labels:
        STATIC = 'Static'
        PERCENTAGE = 'Percentage'

    def __repr__(self):
        return self.value


class OperationType(Enum):
    DEFAULT = 'DEFAULT'
    MONEY_IN_DD = 'MONEY_IN_DD'
    MONEY_IN_CC = 'MONEY_IN_CC'
    MONEY_IN_BT = 'MONEY_IN_BT'
    MONEY_OUT_BT = 'MONEY_OUT_BT'
    INTERNAL = 'INTERNAL'

    class Labels:
        DEFAULT = 'Default'
        MONEY_IN_DD = 'Income direct debit'
        MONEY_IN_CC = 'Income credit card'
        MONEY_IN_BT = 'Income bank transfer'
        MONEY_OUT_BT = 'Outcome bank transfer'
        INTERNAL = 'Internal'

    def __repr__(self):
        return self.value


class UserStatus(Enum):
    inactive = 'inactive'
    active = 'active'
    blocked = 'blocked'
    banned = 'banned'
    pending = 'pending'

    class Labels:
        inactive = 'Inactive'
        active = 'Active'
        blocked = 'Blocked'
        banned = 'Banned'
        pending = 'Pending'

    def __repr__(self):
        return self.value


class UserRole(Enum):
    admin = 'admin'
    owner = 'owner'
    sub_user = 'sub_user'

    class Labels:
        admin = 'Administrator'
        owner = 'Owner'
        sub_user = 'Sub user'

    def __repr__(self):
        return self.value


class UserTitle(Enum):
    mr = 'mr'
    mrs = 'mrs'
    miss = 'miss'
    ms = 'ms'
    other = 'other'

    class Labels:
        mr = 'Mr'
        mrs = 'Mrs'
        miss = 'Miss'
        ms = 'Ms'
        other = 'Other'

    def __repr__(self):
        return self.value


class Gender(Enum):
    female = 'female'
    male = 'male'
    unknown = 'unknown'

    class Labels:
        female = 'Female'
        male = 'Male'
        unknown = 'Unknown'

    def __repr__(self):
        return self.value


class Country(Enum):
    AF = 'AF'
    AX = 'AX'
    AL = 'AL'
    DZ = 'DZ'
    AS = 'AS'
    AD = 'AD'
    AO = 'AO'
    AI = 'AI'
    AQ = 'AQ'
    AG = 'AG'
    AR = 'AR'
    AM = 'AM'
    AW = 'AW'
    AU = 'AU'
    AT = 'AT'
    AZ = 'AZ'
    BS = 'BS'
    BH = 'BH'
    BD = 'BD'
    BB = 'BB'
    BY = 'BY'
    BE = 'BE'
    BZ = 'BZ'
    BJ = 'BJ'
    BM = 'BM'
    BT = 'BT'
    BO = 'BO'
    BA = 'BA'
    BW = 'BW'
    BR = 'BR'
    IO = 'IO'
    BN = 'BN'
    BG = 'BG'
    BF = 'BF'
    BI = 'BI'
    KH = 'KH'
    CM = 'CM'
    CA = 'CA'
    CV = 'CV'
    KY = 'KY'
    CF = 'CF'
    TD = 'TD'
    CL = 'CL'
    CN = 'CN'
    CX = 'CX'
    CC = 'CC'
    CO = 'CO'
    KM = 'KM'
    CG = 'CG'
    CD = 'CD'
    CK = 'CK'
    CR = 'CR'
    CI = 'CI'
    HR = 'HR'
    CU = 'CU'
    CY = 'CY'
    CZ = 'CZ'
    DK = 'DK'
    DJ = 'DJ'
    DM = 'DM'
    DO = 'DO'
    EC = 'EC'
    EG = 'EG'
    SV = 'SV'
    GQ = 'GQ'
    ER = 'ER'
    EE = 'EE'
    ET = 'ET'
    FK = 'FK'
    FO = 'FO'
    FJ = 'FJ'
    FI = 'FI'
    FR = 'FR'
    GF = 'GF'
    PF = 'PF'
    GA = 'GA'
    GM = 'GM'
    GE = 'GE'
    DE = 'DE'
    GH = 'GH'
    GI = 'GI'
    GR = 'GR'
    GL = 'GL'
    GD = 'GD'
    GP = 'GP'
    GU = 'GU'
    GT = 'GT'
    GG = 'GG'
    GN = 'GN'
    GW = 'GW'
    GY = 'GY'
    HT = 'HT'
    VA = 'VA'
    HN = 'HN'
    HK = 'HK'
    HU = 'HU'
    IS = 'IS'
    IN = 'IN'
    ID = 'ID'
    IR = 'IR'
    IQ = 'IQ'
    IE = 'IE'
    IM = 'IM'
    IL = 'IL'
    IT = 'IT'
    JM = 'JM'
    JP = 'JP'
    JE = 'JE'
    JO = 'JO'
    KZ = 'KZ'
    KE = 'KE'
    KI = 'KI'
    KP = 'KP'
    KR = 'KR'
    KW = 'KW'
    KG = 'KG'
    LA = 'LA'
    LV = 'LV'
    LB = 'LB'
    LS = 'LS'
    LR = 'LR'
    LY = 'LY'
    LI = 'LI'
    LT = 'LT'
    LU = 'LU'
    MO = 'MO'
    MK = 'MK'
    MG = 'MG'
    MW = 'MW'
    MY = 'MY'
    MV = 'MV'
    ML = 'ML'
    MT = 'MT'
    MH = 'MH'
    MQ = 'MQ'
    MR = 'MR'
    MU = 'MU'
    YT = 'YT'
    MX = 'MX'
    FM = 'FM'
    MD = 'MD'
    MC = 'MC'
    MN = 'MN'
    ME = 'ME'
    MS = 'MS'
    MA = 'MA'
    MZ = 'MZ'
    MM = 'MM'
    NA = 'NA'
    NR = 'NR'
    NP = 'NP'
    NL = 'NL'
    AN = 'AN'
    NC = 'NC'
    NZ = 'NZ'
    NI = 'NI'
    NE = 'NE'
    NG = 'NG'
    NU = 'NU'
    NF = 'NF'
    MP = 'MP'
    NO = 'NO'
    OM = 'OM'
    PK = 'PK'
    PW = 'PW'
    PS = 'PS'
    PA = 'PA'
    PG = 'PG'
    PY = 'PY'
    PE = 'PE'
    PH = 'PH'
    PN = 'PN'
    PL = 'PL'
    PT = 'PT'
    PR = 'PR'
    QA = 'QA'
    RO = 'RO'
    RU = 'RU'
    RW = 'RW'
    RE = 'RE'
    BL = 'BL'
    SH = 'SH'
    KN = 'KN'
    LC = 'LC'
    MF = 'MF'
    PM = 'PM'
    VC = 'VC'
    WS = 'WS'
    SM = 'SM'
    ST = 'ST'
    SA = 'SA'
    SN = 'SN'
    RS = 'RS'
    SC = 'SC'
    SL = 'SL'
    SG = 'SG'
    SK = 'SK'
    SI = 'SI'
    SB = 'SB'
    SO = 'SO'
    ZA = 'ZA'
    SS = 'SS'
    GS = 'GS'
    ES = 'ES'
    LK = 'LK'
    SD = 'SD'
    SR = 'SR'
    SJ = 'SJ'
    SZ = 'SZ'
    SE = 'SE'
    CH = 'CH'
    SY = 'SY'
    TW = 'TW'
    TJ = 'TJ'
    TZ = 'TZ'
    TH = 'TH'
    TL = 'TL'
    TG = 'TG'
    TK = 'TK'
    TO = 'TO'
    TT = 'TT'
    TN = 'TN'
    TR = 'TR'
    TM = 'TM'
    TC = 'TC'
    TV = 'TV'
    UG = 'UG'
    UA = 'UA'
    AE = 'AE'
    GB = 'GB'
    US = 'US'
    UY = 'UY'
    UZ = 'UZ'
    VU = 'VU'
    VE = 'VE'
    VN = 'VN'
    VG = 'VG'
    VI = 'VI'
    WF = 'WF'
    YE = 'YE'
    ZM = 'ZM'
    ZW = 'ZW'

    class Labels:
        AF = 'Afghanistan'
        AX = 'Aland Islands'
        AL = 'Albania'
        DZ = 'Algeria'
        AS = 'AmericanSamoa'
        AD = 'Andorra'
        AO = 'Angola'
        AI = 'Anguilla'
        AQ = 'Antarctica'
        AG = 'Antigua and Barbuda'
        AR = 'Argentina'
        AM = 'Armenia'
        AW = 'Aruba'
        AU = 'Australia'
        AT = 'Austria'
        AZ = 'Azerbaijan'
        BS = 'Bahamas'
        BH = 'Bahrain'
        BD = 'Bangladesh'
        BB = 'Barbados'
        BY = 'Belarus'
        BE = 'Belgium'
        BZ = 'Belize'
        BJ = 'Benin'
        BM = 'Bermuda'
        BT = 'Bhutan'
        BO = 'Bolivia, Plurinational State of'
        BA = 'Bosnia and Herzegovina'
        BW = 'Botswana'
        BR = 'Brazil'
        IO = 'British Indian Ocean Territory'
        BN = 'Brunei Darussalam'
        BG = 'Bulgaria'
        BF = 'Burkina Faso'
        BI = 'Burundi'
        KH = 'Cambodia'
        CM = 'Cameroon'
        CA = 'Canada'
        CV = 'Cape Verde'
        KY = 'Cayman Islands'
        CF = 'Central African Republic'
        TD = 'Chad'
        CL = 'Chile'
        CN = 'China'
        CX = 'Christmas Island'
        CC = 'Cocos (Keeling) Islands'
        CO = 'Colombia'
        KM = 'Comoros'
        CG = 'Congo'
        CD = 'Congo, The Democratic Republic of the Congo'
        CK = 'Cook Islands'
        CR = 'Costa Rica'
        CI = "Cote d'Ivoire"
        HR = 'Croatia'
        CU = 'Cuba'
        CY = 'Cyprus'
        CZ = 'Czech Republic'
        DK = 'Denmark'
        DJ = 'Djibouti'
        DM = 'Dominica'
        DO = 'Dominican Republic'
        EC = 'Ecuador'
        EG = 'Egypt'
        SV = 'El Salvador'
        GQ = 'Equatorial Guinea'
        ER = 'Eritrea'
        EE = 'Estonia'
        ET = 'Ethiopia'
        FK = 'Falkland Islands (Malvinas)'
        FO = 'Faroe Islands'
        FJ = 'Fiji'
        FI = 'Finland'
        FR = 'France'
        GF = 'French Guiana'
        PF = 'French Polynesia'
        GA = 'Gabon'
        GM = 'Gambia'
        GE = 'Georgia'
        DE = 'Germany'
        GH = 'Ghana'
        GI = 'Gibraltar'
        GR = 'Greece'
        GL = 'Greenland'
        GD = 'Grenada'
        GP = 'Guadeloupe'
        GU = 'Guam'
        GT = 'Guatemala'
        GG = 'Guernsey'
        GN = 'Guinea'
        GW = 'Guinea-Bissau'
        GY = 'Guyana'
        HT = 'Haiti'
        VA = 'Holy See (Vatican City State)'
        HN = 'Honduras'
        HK = 'Hong Kong'
        HU = 'Hungary'
        IS = 'Iceland'
        IN = 'India'
        ID = 'Indonesia'
        IR = 'Iran, Islamic Republic of Persian Gulf'
        IQ = 'Iraq'
        IE = 'Ireland'
        IM = 'Isle of Man'
        IL = 'Israel'
        IT = 'Italy'
        JM = 'Jamaica'
        JP = 'Japan'
        JE = 'Jersey'
        JO = 'Jordan'
        KZ = 'Kazakhstan'
        KE = 'Kenya'
        KI = 'Kiribati'
        KP = "Korea, Democratic People's Republic of Korea"
        KR = 'Korea, Republic of South Korea'
        KW = 'Kuwait'
        KG = 'Kyrgyzstan'
        LA = 'Laos'
        LV = 'Latvia'
        LB = 'Lebanon'
        LS = 'Lesotho'
        LR = 'Liberia'
        LY = 'Libyan Arab Jamahiriya'
        LI = 'Liechtenstein'
        LT = 'Lithuania'
        LU = 'Luxembourg'
        MO = 'Macao'
        MK = 'Macedonia'
        MG = 'Madagascar'
        MW = 'Malawi'
        MY = 'Malaysia'
        MV = 'Maldives'
        ML = 'Mali'
        MT = 'Malta'
        MH = 'Marshall Islands'
        MQ = 'Martinique'
        MR = 'Mauritania'
        MU = 'Mauritius'
        YT = 'Mayotte'
        MX = 'Mexico'
        FM = 'Micronesia, Federated States of Micronesia'
        MD = 'Moldova'
        MC = 'Monaco'
        MN = 'Mongolia'
        ME = 'Montenegro'
        MS = 'Montserrat'
        MA = 'Morocco'
        MZ = 'Mozambique'
        MM = 'Myanmar'
        NA = 'Namibia'
        NR = 'Nauru'
        NP = 'Nepal'
        NL = 'Netherlands'
        AN = 'Netherlands Antilles'
        NC = 'New Caledonia'
        NZ = 'New Zealand'
        NI = 'Nicaragua'
        NE = 'Niger'
        NG = 'Nigeria'
        NU = 'Niue'
        NF = 'Norfolk Island'
        MP = 'Northern Mariana Islands'
        NO = 'Norway'
        OM = 'Oman'
        PK = 'Pakistan'
        PW = 'Palau'
        PS = 'Palestinian Territory, Occupied'
        PA = 'Panama'
        PG = 'Papua New Guinea'
        PY = 'Paraguay'
        PE = 'Peru'
        PH = 'Philippines'
        PN = 'Pitcairn'
        PL = 'Poland'
        PT = 'Portugal'
        PR = 'Puerto Rico'
        QA = 'Qatar'
        RO = 'Romania'
        RU = 'Russia'
        RW = 'Rwanda'
        RE = 'Reunion'
        BL = 'Saint Barthelemy'
        SH = 'Saint Helena, Ascension and Tristan Da Cunha'
        KN = 'Saint Kitts and Nevis'
        LC = 'Saint Lucia'
        MF = 'Saint Martin'
        PM = 'Saint Pierre and Miquelon'
        VC = 'Saint Vincent and the Grenadines'
        WS = 'Samoa'
        SM = 'San Marino'
        ST = 'Sao Tome and Principe'
        SA = 'Saudi Arabia'
        SN = 'Senegal'
        RS = 'Serbia'
        SC = 'Seychelles'
        SL = 'Sierra Leone'
        SG = 'Singapore'
        SK = 'Slovakia'
        SI = 'Slovenia'
        SB = 'Solomon Islands'
        SO = 'Somalia'
        ZA = 'South Africa'
        SS = 'South Sudan'
        GS = 'South Georgia and the South Sandwich Islands'
        ES = 'Spain'
        LK = 'Sri Lanka'
        SD = 'Sudan'
        SR = 'Suriname'
        SJ = 'Svalbard and Jan Mayen'
        SZ = 'Swaziland'
        SE = 'Sweden'
        CH = 'Switzerland'
        SY = 'Syrian Arab Republic'
        TW = 'Taiwan'
        TJ = 'Tajikistan'
        TZ = 'Tanzania, United Republic of Tanzania'
        TH = 'Thailand'
        TL = 'Timor-Leste'
        TG = 'Togo'
        TK = 'Tokelau'
        TO = 'Tonga'
        TT = 'Trinidad and Tobago'
        TN = 'Tunisia'
        TR = 'Turkey'
        TM = 'Turkmenistan'
        TC = 'Turks and Caicos Islands'
        TV = 'Tuvalu'
        UG = 'Uganda'
        UA = 'Ukraine'
        AE = 'United Arab Emirates'
        GB = 'United Kingdom'
        US = 'United States'
        UY = 'Uruguay'
        UZ = 'Uzbekistan'
        VU = 'Vanuatu'
        VE = 'Venezuela, Bolivarian Republic of Venezuela'
        VN = 'Vietnam'
        VG = 'Virgin Islands, British'
        VI = 'Virgin Islands, U.S.'
        WF = 'Wallis and Futuna'
        YE = 'Yemen'
        ZM = 'Zambia'
        ZW = 'Zimbabwe'

    def __repr__(self):
        return self.value


class CountryDialCode(Enum):
    AF = '+93'
    AX = '+358'
    AL = '+355'
    DZ = '+213'
    AS = '+1684'
    AD = '+376'
    AO = '+244'
    AI = '+1264'
    AQ = '+672'
    AG = '+1268'
    AR = '+54'
    AM = '+374'
    AW = '+297'
    AU = '+61'
    AT = '+43'
    AZ = '+994'
    BS = '+1242'
    BH = '+973'
    BD = '+880'
    BB = '+1246'
    BY = '+375'
    BE = '+32'
    BZ = '+501'
    BJ = '+229'
    BM = '+1441'
    BT = '+975'
    BO = '+591'
    BA = '+387'
    BW = '+267'
    BR = '+55'
    IO = '+246'
    BN = '+673'
    BG = '+359'
    BF = '+226'
    BI = '+257'
    KH = '+855'
    CM = '+237'
    CA = '+1'
    CV = '+238'
    KY = '+ 345'
    CF = '+236'
    TD = '+235'
    CL = '+56'
    CN = '+86'
    CX = '+61'
    CC = '+61'
    CO = '+57'
    KM = '+269'
    CG = '+242'
    CD = '+243'
    CK = '+682'
    CR = '+506'
    CI = '+225'
    HR = '+385'
    CU = '+53'
    CY = '+357'
    CZ = '+420'
    DK = '+45'
    DJ = '+253'
    DM = '+1767'
    DO = '+1849'
    EC = '+593'
    EG = '+20'
    SV = '+503'
    GQ = '+240'
    ER = '+291'
    EE = '+372'
    ET = '+251'
    FK = '+500'
    FO = '+298'
    FJ = '+679'
    FI = '+358'
    FR = '+33'
    GF = '+594'
    PF = '+689'
    GA = '+241'
    GM = '+220'
    GE = '+995'
    DE = '+49'
    GH = '+233'
    GI = '+350'
    GR = '+30'
    GL = '+299'
    GD = '+1473'
    GP = '+590'
    GU = '+1671'
    GT = '+502'
    GG = '+44'
    GN = '+224'
    GW = '+245'
    GY = '+595'
    HT = '+509'
    VA = '+379'
    HN = '+504'
    HK = '+852'
    HU = '+36'
    IS = '+354'
    IN = '+91'
    ID = '+62'
    IR = '+98'
    IQ = '+964'
    IE = '+353'
    IM = '+44'
    IL = '+972'
    IT = '+39'
    JM = '+1876'
    JP = '+81'
    JE = '+44'
    JO = '+962'
    KZ = '+77'
    KE = '+254'
    KI = '+686'
    KP = '+850'
    KR = '+82'
    KW = '+965'
    KG = '+996'
    LA = '+856'
    LV = '+371'
    LB = '+961'
    LS = '+266'
    LR = '+231'
    LY = '+218'
    LI = '+423'
    LT = '+370'
    LU = '+352'
    MO = '+853'
    MK = '+389'
    MG = '+261'
    MW = '+265'
    MY = '+60'
    MV = '+960'
    ML = '+223'
    MT = '+356'
    MH = '+692'
    MQ = '+596'
    MR = '+222'
    MU = '+230'
    YT = '+262'
    MX = '+52'
    FM = '+691'
    MD = '+373'
    MC = '+377'
    MN = '+976'
    ME = '+382'
    MS = '+1664'
    MA = '+212'
    MZ = '+258'
    MM = '+95'
    NA = '+264'
    NR = '+674'
    NP = '+977'
    NL = '+31'
    AN = '+599'
    NC = '+687'
    NZ = '+64'
    NI = '+505'
    NE = '+227'
    NG = '+234'
    NU = '+683'
    NF = '+672'
    MP = '+1670'
    NO = '+47'
    OM = '+968'
    PK = '+92'
    PW = '+680'
    PS = '+970'
    PA = '+507'
    PG = '+675'
    PY = '+595'
    PE = '+51'
    PH = '+63'
    PN = '+872'
    PL = '+48'
    PT = '+351'
    PR = '+1939'
    QA = '+974'
    RO = '+40'
    RU = '+7'
    RW = '+250'
    RE = '+262'
    BL = '+590'
    SH = '+290'
    KN = '+1869'
    LC = '+1758'
    MF = '+590'
    PM = '+508'
    VC = '+1784'
    WS = '+685'
    SM = '+378'
    ST = '+239'
    SA = '+966'
    SN = '+221'
    RS = '+381'
    SC = '+248'
    SL = '+232'
    SG = '+65'
    SK = '+421'
    SI = '+386'
    SB = '+677'
    SO = '+252'
    ZA = '+27'
    SS = '+211'
    GS = '+500'
    ES = '+34'
    LK = '+94'
    SD = '+249'
    SR = '+597'
    SJ = '+47'
    SZ = '+268'
    SE = '+46'
    CH = '+41'
    SY = '+963'
    TW = '+886'
    TJ = '+992'
    TZ = '+255'
    TH = '+66'
    TL = '+670'
    TG = '+228'
    TK = '+690'
    TO = '+676'
    TT = '+1868'
    TN = '+216'
    TR = '+90'
    TM = '+993'
    TC = '+1649'
    TV = '+688'
    UG = '+256'
    UA = '+380'
    AE = '+971'
    GB = '+44'
    US = '+1'
    UY = '+598'
    UZ = '+998'
    VU = '+678'
    VE = '+58'
    VN = '+84'
    VG = '+1284'
    VI = '+1340'
    WF = '+681'
    YE = '+967'
    ZM = '+260'
    ZW = '+263'

    class Labels:
        AF = 'Afghanistan'
        AX = 'Aland Islands'
        AL = 'Albania'
        DZ = 'Algeria'
        AS = 'AmericanSamoa'
        AD = 'Andorra'
        AO = 'Angola'
        AI = 'Anguilla'
        AQ = 'Antarctica'
        AG = 'Antigua and Barbuda'
        AR = 'Argentina'
        AM = 'Armenia'
        AW = 'Aruba'
        AU = 'Australia'
        AT = 'Austria'
        AZ = 'Azerbaijan'
        BS = 'Bahamas'
        BH = 'Bahrain'
        BD = 'Bangladesh'
        BB = 'Barbados'
        BY = 'Belarus'
        BE = 'Belgium'
        BZ = 'Belize'
        BJ = 'Benin'
        BM = 'Bermuda'
        BT = 'Bhutan'
        BO = 'Bolivia, Plurinational State of'
        BA = 'Bosnia and Herzegovina'
        BW = 'Botswana'
        BR = 'Brazil'
        IO = 'British Indian Ocean Territory'
        BN = 'Brunei Darussalam'
        BG = 'Bulgaria'
        BF = 'Burkina Faso'
        BI = 'Burundi'
        KH = 'Cambodia'
        CM = 'Cameroon'
        CA = 'Canada'
        CV = 'Cape Verde'
        KY = 'Cayman Islands'
        CF = 'Central African Republic'
        TD = 'Chad'
        CL = 'Chile'
        CN = 'China'
        CX = 'Christmas Island'
        CC = 'Cocos (Keeling) Islands'
        CO = 'Colombia'
        KM = 'Comoros'
        CG = 'Congo'
        CD = 'Congo, The Democratic Republic of the Congo'
        CK = 'Cook Islands'
        CR = 'Costa Rica'
        CI = "Cote d'Ivoire"
        HR = 'Croatia'
        CU = 'Cuba'
        CY = 'Cyprus'
        CZ = 'Czech Republic'
        DK = 'Denmark'
        DJ = 'Djibouti'
        DM = 'Dominica'
        DO = 'Dominican Republic'
        EC = 'Ecuador'
        EG = 'Egypt'
        SV = 'El Salvador'
        GQ = 'Equatorial Guinea'
        ER = 'Eritrea'
        EE = 'Estonia'
        ET = 'Ethiopia'
        FK = 'Falkland Islands (Malvinas)'
        FO = 'Faroe Islands'
        FJ = 'Fiji'
        FI = 'Finland'
        FR = 'France'
        GF = 'French Guiana'
        PF = 'French Polynesia'
        GA = 'Gabon'
        GM = 'Gambia'
        GE = 'Georgia'
        DE = 'Germany'
        GH = 'Ghana'
        GI = 'Gibraltar'
        GR = 'Greece'
        GL = 'Greenland'
        GD = 'Grenada'
        GP = 'Guadeloupe'
        GU = 'Guam'
        GT = 'Guatemala'
        GG = 'Guernsey'
        GN = 'Guinea'
        GW = 'Guinea-Bissau'
        GY = 'Guyana'
        HT = 'Haiti'
        VA = 'Holy See (Vatican City State)'
        HN = 'Honduras'
        HK = 'Hong Kong'
        HU = 'Hungary'
        IS = 'Iceland'
        IN = 'India'
        ID = 'Indonesia'
        IR = 'Iran, Islamic Republic of Persian Gulf'
        IQ = 'Iraq'
        IE = 'Ireland'
        IM = 'Isle of Man'
        IL = 'Israel'
        IT = 'Italy'
        JM = 'Jamaica'
        JP = 'Japan'
        JE = 'Jersey'
        JO = 'Jordan'
        KZ = 'Kazakhstan'
        KE = 'Kenya'
        KI = 'Kiribati'
        KP = "Korea, Democratic People's Republic of Korea"
        KR = 'Korea, Republic of South Korea'
        KW = 'Kuwait'
        KG = 'Kyrgyzstan'
        LA = 'Laos'
        LV = 'Latvia'
        LB = 'Lebanon'
        LS = 'Lesotho'
        LR = 'Liberia'
        LY = 'Libyan Arab Jamahiriya'
        LI = 'Liechtenstein'
        LT = 'Lithuania'
        LU = 'Luxembourg'
        MO = 'Macao'
        MK = 'Macedonia'
        MG = 'Madagascar'
        MW = 'Malawi'
        MY = 'Malaysia'
        MV = 'Maldives'
        ML = 'Mali'
        MT = 'Malta'
        MH = 'Marshall Islands'
        MQ = 'Martinique'
        MR = 'Mauritania'
        MU = 'Mauritius'
        YT = 'Mayotte'
        MX = 'Mexico'
        FM = 'Micronesia, Federated States of Micronesia'
        MD = 'Moldova'
        MC = 'Monaco'
        MN = 'Mongolia'
        ME = 'Montenegro'
        MS = 'Montserrat'
        MA = 'Morocco'
        MZ = 'Mozambique'
        MM = 'Myanmar'
        NA = 'Namibia'
        NR = 'Nauru'
        NP = 'Nepal'
        NL = 'Netherlands'
        AN = 'Netherlands Antilles'
        NC = 'New Caledonia'
        NZ = 'New Zealand'
        NI = 'Nicaragua'
        NE = 'Niger'
        NG = 'Nigeria'
        NU = 'Niue'
        NF = 'Norfolk Island'
        MP = 'Northern Mariana Islands'
        NO = 'Norway'
        OM = 'Oman'
        PK = 'Pakistan'
        PW = 'Palau'
        PS = 'Palestinian Territory, Occupied'
        PA = 'Panama'
        PG = 'Papua New Guinea'
        PY = 'Paraguay'
        PE = 'Peru'
        PH = 'Philippines'
        PN = 'Pitcairn'
        PL = 'Poland'
        PT = 'Portugal'
        PR = 'Puerto Rico'
        QA = 'Qatar'
        RO = 'Romania'
        RU = 'Russia'
        RW = 'Rwanda'
        RE = 'Reunion'
        BL = 'Saint Barthelemy'
        SH = 'Saint Helena, Ascension and Tristan Da Cunha'
        KN = 'Saint Kitts and Nevis'
        LC = 'Saint Lucia'
        MF = 'Saint Martin'
        PM = 'Saint Pierre and Miquelon'
        VC = 'Saint Vincent and the Grenadines'
        WS = 'Samoa'
        SM = 'San Marino'
        ST = 'Sao Tome and Principe'
        SA = 'Saudi Arabia'
        SN = 'Senegal'
        RS = 'Serbia'
        SC = 'Seychelles'
        SL = 'Sierra Leone'
        SG = 'Singapore'
        SK = 'Slovakia'
        SI = 'Slovenia'
        SB = 'Solomon Islands'
        SO = 'Somalia'
        ZA = 'South Africa'
        SS = 'South Sudan'
        GS = 'South Georgia and the South Sandwich Islands'
        ES = 'Spain'
        LK = 'Sri Lanka'
        SD = 'Sudan'
        SR = 'Suriname'
        SJ = 'Svalbard and Jan Mayen'
        SZ = 'Swaziland'
        SE = 'Sweden'
        CH = 'Switzerland'
        SY = 'Syrian Arab Republic'
        TW = 'Taiwan'
        TJ = 'Tajikistan'
        TZ = 'Tanzania, United Republic of Tanzania'
        TH = 'Thailand'
        TL = 'Timor-Leste'
        TG = 'Togo'
        TK = 'Tokelau'
        TO = 'Tonga'
        TT = 'Trinidad and Tobago'
        TN = 'Tunisia'
        TR = 'Turkey'
        TM = 'Turkmenistan'
        TC = 'Turks and Caicos Islands'
        TV = 'Tuvalu'
        UG = 'Uganda'
        UA = 'Ukraine'
        AE = 'United Arab Emirates'
        GB = 'United Kingdom'
        US = 'United States'
        UY = 'Uruguay'
        UZ = 'Uzbekistan'
        VU = 'Vanuatu'
        VE = 'Venezuela, Bolivarian Republic of Venezuela'
        VN = 'Vietnam'
        VG = 'Virgin Islands, British'
        VI = 'Virgin Islands, U.S.'
        WF = 'Wallis and Futuna'
        YE = 'Yemen'
        ZM = 'Zambia'
        ZW = 'Zimbabwe'

    def __repr__(self):
        return self.value


class Dataset(object):

    @staticmethod
    def all():
        return {
            'titles': [title.label for title in UserTitle],
            'genders': [gender.label for gender in Gender],
            'countriesAvailable': [{
                'iso': country.value,
                'name': country.label,
                'phoneCode': CountryDialCode[country.value].value
            } for country in Country if (country.value in COUNTRIES_AVAILABLE)],
            'countriesAll': [{
                'iso': country.value,
                'name': country.label,
                'phoneCode': CountryDialCode[country.value].value
            } for country in Country]
        }

    @staticmethod
    def available_country_codes():
        return COUNTRIES_AVAILABLE
