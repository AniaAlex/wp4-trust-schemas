"""Where the text of ETSI TS 119 602 V1.1.1 defines each component, data type and rule: clause, title, kind, the
names the text uses (more than one where the text contradicts itself), presence as the text states it, and verbatim
quotes. build_model.py links every model component, value type and constraint to one of these sources by id and
verifies every quote against the text (page and line are computed; a quote found more than once is flagged ambiguous).

Edit here to add or correct a citation. Formerly the "text" part of the component matrix (docs/matrix/, removed
2026-10-09)."""

SOURCES = {
    '6.1.2/URI': {
        'clause': '6.1.2', 'title': 'URI', 'kind': 'datatype',
        'names': ['URI'], 'presence': 'n/a',
        'quotes': [
            'implementers shall use general syntax as specified by IETF RFC 3986',
        ]},
    '6.1.3/DateTime': {
        'clause': '6.1.3', 'title': 'Date-time', 'kind': 'datatype',
        'names': ['date-time'], 'presence': 'n/a',
        'quotes': [
            'minute, second (without decimal fraction) and the UTC designator "Z"',
        ]},
    '6.1.4/MultiLangString': {
        'clause': '6.1.4', 'title': 'Multilingual character string', 'kind': 'datatype',
        'names': ['multilingual character string'], 'presence': 'n/a',
        'quotes': [
            'Each multilingual character string shall consist of two parts: a tag, conformant to IETF RFC 5646 [11] and in lower case',
        ]},
    '6.1.4/English': {
        'clause': '6.1.4', 'title': 'English version required', 'kind': 'rule',
        'names': ['en'], 'presence': 'every multilingual sequence (interpretation 2)',
        'quotes': [
            'Lists of trusted entities shall be issued supporting at least the UK English language',
        ]},
    '6.1.4/MultiLangURI': {
        'clause': '6.1.4', 'title': 'Multilingual pointer', 'kind': 'datatype',
        'names': ['multilingual pointer'], 'presence': 'n/a',
        'quotes': [
            'A multilingual pointer shall be a URI that identifies a resource expressed in a particular language.',
        ]},
    '6.1.5/CountryCode': {
        'clause': '6.1.5', 'title': 'Country code', 'kind': 'datatype',
        'names': ['CC'], 'presence': 'n/a',
        'quotes': [
            'All fields carrying Country Codes values, denoted by "CC", shall be in capital letters',
        ]},
    'B.2/PlainText': {
        'clause': 'B.2', 'title': 'Multilingual string content', 'kind': 'rule',
        'names': ['multilingual character string'], 'presence': 'n/a',
        'quotes': [
            'control characters such as TAB, CR, LF shall not be present',
        ]},
    '5/LoTE': {
        'clause': '5', 'title': 'List of trusted entities (root)', 'kind': 'component',
        'names': ['LoTE'], 'presence': '1',
        'quotes': [
            'There shall be only one occurrence of the first two and last components',
        ]},
    '6.2/LoTETag': {
        'clause': '6.2', 'title': 'LoTE tag', 'kind': 'component',
        'names': ['LoTETag'], 'presence': '1 (clause 5)',
        'quotes': [
            'The LoTETag component shall be a character string which indicates that the data structure is a LoTE.',
        ]},
    '6.8/Signature': {
        'clause': '6.8.0', 'title': 'Digital signature', 'kind': 'component',
        'names': ['Signature'], 'presence': '0..1',
        'quotes': [
            'If the AdES digital signature is present within the LoTE itself, it shall be provided through the Signature component',
        ]},
    '6.3/ListAndSchemeInformation': {
        'clause': '6.3.0', 'title': 'List and scheme information', 'kind': 'component',
        'names': ['ListAndSchemeInformation'], 'presence': 'implicit 0..1 (need not contain); explicit 1',
        'quotes': [
            'In case the scheme information is implicit, the LoTE need not contain this component.',
            'In case the scheme information is explicit the LoTE shall contain this component.',
        ]},
    '6.3/Table1': {
        'clause': '6.3.0', 'title': 'Implicit vs explicit scheme information (Table 1)', 'kind': 'rule',
        'names': ['ListAndSchemeInformation'], 'presence': 'implicit: 5 elements; explicit: 13',
        'quotes': [
            'In case the scheme information is explicit this component shall contain, in addition, LoTEType, the SchemeInformationURI, the StatusDeterminationApproach, the SchemeTypeCommunityRules, the SchemeTerritory, and the PolicyOrLegalNotice elements.',
        ]},
    '6.3.1/LoTEVersionIdentifier': {
        'clause': '6.3.1', 'title': 'LoTE version identifier', 'kind': 'component',
        'names': ['LoTEVersionIdentifier'], 'presence': '1',
        'quotes': [
            'The LoTEVersionIdentifier component shall contain an integer.',
        ]},
    '6.3.2/LoTESequenceNumber': {
        'clause': '6.3.2', 'title': 'LoTE sequence number', 'kind': 'component',
        'names': ['LoTESequenceNumber'], 'presence': '1',
        'quotes': [
            'At the first release of the LoTE, the value of the sequence number shall be 1.',
        ]},
    '6.3.3/LoTEType': {
        'clause': '6.3.3', 'title': 'LoTE type', 'kind': 'component',
        'names': ['LoTEType'], 'presence': 'implicit O / explicit M',
        'quotes': [
            'The LoTEType component shall contain an indicator expressed as a URI.',
        ]},
    '6.3.4/SchemeOperatorName': {
        'clause': '6.3.4', 'title': 'Scheme operator name', 'kind': 'component',
        'names': ['SchemeOperatorName'], 'presence': '1',
        'quotes': [
            'The SchemeOperatorName component shall contain a sequence of multilingual character strings (see clause 6.1.4).',
        ]},
    '6.3.5/SchemeOperatorAddress': {
        'clause': '6.3.5.0', 'title': 'Scheme operator address', 'kind': 'component',
        'names': ['SchemeOperatorAddress'], 'presence': 'implicit O / explicit M',
        'quotes': [
            'the PostalAddresses element specified in clause 6.3.5.1; and',
        ]},
    '6.3.5.1/PostalAddresses': {
        'clause': '6.3.5.1', 'title': 'Scheme operator postal address', 'kind': 'component',
        'names': ['PostalAddresses'], 'presence': '1',
        'quotes': [
            'The PostalAddresses component specifies the postal address of the legal entity identified in clause 6.3.4',
        ]},
    '6.3.5.1/StreetAddress': {
        'clause': '6.3.5.1', 'title': 'Street address', 'kind': 'component',
        'names': ['StreetAddress'], 'presence': '1',
        'quotes': [
            'The StreetAddress element, which shall be a string.',
        ]},
    '6.3.5.1/Locality': {
        'clause': '6.3.5.1', 'title': 'Locality', 'kind': 'component',
        'names': ['Locality'], 'presence': '0..1',
        'quotes': [
            'The Locality element, which shall be a string.',
        ]},
    '6.3.5.1/StateOrProvince': {
        'clause': '6.3.5.1', 'title': 'State or province', 'kind': 'component',
        'names': ['StateOrProvince'], 'presence': '0..1',
        'quotes': [
            'The StateOrProvince element, which shall be a string.',
        ]},
    '6.3.5.1/PostalCode': {
        'clause': '6.3.5.1', 'title': 'Postal code', 'kind': 'component',
        'names': ['PostalCode'], 'presence': '0..1',
        'quotes': [
            'The PostalCode element, which shall be a string.',
        ]},
    '6.3.5.1/Country': {
        'clause': '6.3.5.1', 'title': 'Country', 'kind': 'component',
        'names': ['Country'], 'presence': '1',
        'quotes': [
            'The Country element, which shall be a two-character code in accordance with clause 6.1.5 (a).',
        ]},
    '6.3.5.2/ElectronicAddress': {
        'clause': '6.3.5.2', 'title': 'Scheme operator electronic address', 'kind': 'component',
        'names': ['ElectronicAddress'], 'presence': '1',
        'quotes': [
            'mandatorily, an e-mail address as a URI',
        ]},
    '6.3.6/SchemeName': {
        'clause': '6.3.6', 'title': 'Scheme name', 'kind': 'component',
        'names': ['SchemeName'], 'presence': 'implicit / ; explicit M',
        'quotes': [
            'The SchemeName component specifies the name under which the scheme operates.',
            "'CC' is the code used in the 'Scheme territory' element (clause 6.3.10)",
        ]},
    '6.3.7/SchemeInformationURI': {
        'clause': '6.3.7', 'title': 'Scheme information URI', 'kind': 'component',
        'names': ['SchemeInformationURI'], 'presence': 'implicit / ; explicit M',
        'quotes': [
            'This component shall be a sequence of multilingual pointers (see clause 6.1.4).',
        ]},
    '6.3.8/StatusDeterminationApproach': {
        'clause': '6.3.8', 'title': 'Status determination approach', 'kind': 'component',
        'names': ['StatusDeterminationApproach'], 'presence': 'implicit / ; explicit M',
        'quotes': [
            'The StatusDeterminationApproach component shall contain an indicator expressed as a URI.',
        ]},
    '6.3.9/SchemeTypeCommunityRules': {
        'clause': '6.3.9', 'title': 'Scheme type/community/rules', 'kind': 'component',
        'names': ['SchemeTypeCommunityRules'], 'presence': 'implicit / ; explicit M',
        'quotes': [
            'The SchemeTypeCommunityRules component shall contain a sequence of multilingual pointers (see clause 6.1.4).',
        ]},
    '6.3.10/SchemeTerritory': {
        'clause': '6.3.10', 'title': 'Scheme territory', 'kind': 'component',
        'names': ['SchemeTerritory'], 'presence': 'implicit O / explicit M',
        'quotes': [
            'The SchemeTerritory component shall contain a character string in accordance with clause 6.1.5.',
        ]},
    '6.3.11/PolicyOrLegalNotice': {
        'clause': '6.3.11', 'title': 'LoTE policy/legal notice', 'kind': 'component',
        'names': ['PolicyOrLegalNotice'], 'presence': 'implicit / ; explicit M',
        'quotes': [
            'a sequence of LoTEPolicy elements which shall be multilingual pointers',
        ]},
    '6.3.11/LoTELegalNotice': {
        'clause': '6.3.11', 'title': 'LoTE legal notice', 'kind': 'component',
        'names': ['LoTELegalNotice'], 'presence': '1..n (in the choice)',
        'quotes': [
            'a sequence of LoTELegalNotice elements which shall be multilingual character strings',
        ]},
    '6.3.12/HistoricalInformationPeriod': {
        'clause': '6.3.12', 'title': 'Historical information period', 'kind': 'component',
        'names': ['HistoricalInformationPeriod'], 'presence': '0..1',
        'quotes': [
            "When the value of this integer is set to '65535', this signifies that historical information provided in the list of trusted entities shall never be removed.",
        ]},
    '6.3.13/PointersToOtherLoTE': {
        'clause': '6.3.13', 'title': 'Pointers to other LoTEs', 'kind': 'component',
        'names': ['PointersToOtherLoTE', 'PointerToOtherLoTE'], 'presence': '0..1',
        'quotes': [
            'The PointersToOtherLoTE component shall contain a sequence of one or more OtherLoTEPointer elements',
        ]},
    '6.3.13/LoTELocation': {
        'clause': '6.3.13', 'title': 'Pointed-to LoTE location', 'kind': 'component',
        'names': ['LoTELocation'], 'presence': '1',
        'quotes': [
            'a LoTELocation element containing the URI of the machine processable format of another LoTE',
        ]},
    '6.3.13/ServiceDigitalIdentities': {
        'clause': '6.3.13', 'title': 'Digital identities of the pointed-to LoTE issuer', 'kind': 'component',
        'names': ['ServiceDigitalIdentity'], 'presence': '1..n',
        'quotes': [
            'one or more ServiceDigitalIdentity element, all representing the issuer of the LoTE pointed to',
        ]},
    '6.3.13/LoTEQualifiers': {
        'clause': '6.3.13', 'title': 'LoTE qualifiers', 'kind': 'component',
        'names': ['LoTE Qualifiers'], 'presence': '1',
        'quotes': [
            'additional information as a set of LoTE Qualifiers: LoTE Type, as defined in clause 6.3.3; Scheme operator name',
        ]},
    '6.3.13/MimeType': {
        'clause': '6.3.13', 'title': 'MIME type qualifier', 'kind': 'component',
        'names': ['Mime type'], 'presence': '1',
        'quotes': [
            'Scheme territory, as defined in clause 6.3.10; and Mime type.',
        ]},
    '6.3.14/ListIssueDateTime': {
        'clause': '6.3.14', 'title': 'List issue date and time', 'kind': 'component',
        'names': ['ListIssueDateTime'], 'presence': '1',
        'quotes': [
            'The ListIssueDateTime component shall contain a date-time value (see clause 6.1.3).',
        ]},
    '6.3.15/NextUpdate': {
        'clause': '6.3.15', 'title': 'Next update', 'kind': 'component',
        'names': ['NextUpdate'], 'presence': '1',
        'quotes': [
            'or be null to indicate a closed LoTE',
        ]},
    '6.3.16/DistributionPoints': {
        'clause': '6.3.16', 'title': 'Distribution points', 'kind': 'component',
        'names': ['DistributionPoints'], 'presence': '0..1',
        'quotes': [
            'The DistributionPoints component shall contain a non-empty sequence of URIs.',
        ]},
    '6.3.17/SchemeExtensions': {
        'clause': '6.3.17', 'title': 'Scheme extensions', 'kind': 'component',
        'names': ['SchemeExtensions'], 'presence': '0..1',
        'quotes': [
            'Each extension shall have an indication of its criticality.',
        ]},
    '6.4/TrustedEntitiesList': {
        'clause': '6.4.0', 'title': 'Trusted entities list', 'kind': 'component',
        'names': ['TrustedEntitiesList'], 'presence': 'conditional',
        'quotes': [
            'If one or more trusted entity services are or were approved under the LoTE scheme, this component shall be present.',
        ]},
    '6.4.1/TrustedEntity': {
        'clause': '6.4.1', 'title': 'Trusted entity', 'kind': 'component',
        'names': ['TrustedEntity'], 'presence': '1..n',
        'quotes': [
            'The TrustedEntityServices element, which shall be a sequence of TrustedEntityService elements.',
        ]},
    '6.4.3/ServiceHistory': {
        'clause': '6.4.3', 'title': 'Service history', 'kind': 'component',
        'names': ['ServiceHistory'], 'presence': '0..1',
        'quotes': [
            'The ServiceHistory component shall be present only when historical information is applicable to the related service.',
        ]},
    '6.5.1/TEName': {
        'clause': '6.5.1', 'title': 'TE name', 'kind': 'component',
        'names': ['TEName'], 'presence': '1',
        'quotes': [
            'The TEName component shall be a sequence of multilingual character strings (see clause 6.1.4).',
        ]},
    '6.5.2/TETradeName': {
        'clause': '6.5.2', 'title': 'TE trade name', 'kind': 'component',
        'names': ['TETradeName'], 'presence': '0..1',
        'quotes': [
            'The TETradeName component shall be a sequence of multilingual character strings (see clause 6.1.4).',
        ]},
    '6.5.3/TEAddress': {
        'clause': '6.5.3.0', 'title': 'TE address', 'kind': 'component',
        'names': ['TEAddress'], 'presence': '1',
        'quotes': [
            'The TEAddress component shall contain the below sub-components:',
        ]},
    '6.5.3.1/TEPostalAddress': {
        'clause': '6.5.3.1', 'title': 'TE postal address', 'kind': 'component',
        'names': ['TEPostalAddress'], 'presence': '1',
        'quotes': [
            'The TEPostalAddress element (see clause 6.5.3.1).',
        ]},
    '6.5.3.2/TEElectronicAddress': {
        'clause': '6.5.3.2', 'title': 'TE electronic address', 'kind': 'component',
        'names': ['TEElectronicAddress'], 'presence': '1',
        'quotes': [
            'The TEElectronicAddress component specifies an email address, a web-site URI, and an optional telephone',
        ]},
    '6.5.4/TEInformationURI': {
        'clause': '6.5.4', 'title': 'TE information URI', 'kind': 'component',
        'names': ['TEInformationURI'], 'presence': '1',
        'quotes': [
            'The TEInformationURI component shall be a sequence of multilingual pointers (see clause 6.1.4).',
        ]},
    '6.5.5/TEInformationExtensions': {
        'clause': '6.5.5.0', 'title': 'TE information extensions', 'kind': 'component',
        'names': ['TEInformationExtensions'], 'presence': '0..1',
        'quotes': [
            'The TEInformationExtensions component may be used by scheme operators to provide specific TE-related',
        ]},
    '6.5.5.1/OtherAssociatedBodies': {
        'clause': '6.5.5.1.0', 'title': 'Other associated bodies extension', 'kind': 'component',
        'names': ['OtherAssociatedBodies'], 'presence': '0..1',
        'quotes': [
            'The OtherAssociatedBodies component shall be a sequence of AssociatedBody elements which is defined',
        ]},
    '6.5.5.1/AssociatedBodyName': {
        'clause': '6.5.5.1.2', 'title': 'Associated body name', 'kind': 'component',
        'names': ['AssociatedBodyName', 'AssocitedBodyName'], 'presence': '1',
        'quotes': [
            'The AssociatedBodyName component shall be a sequence of multilingual character strings (see clause 6.1.4).',
        ]},
    '6.5.5.1/AssociatedBodyTradeName': {
        'clause': '6.5.5.1.3', 'title': 'Associated body trade name', 'kind': 'component',
        'names': ['AssociatedBodyTradeName'], 'presence': '0..1',
        'quotes': [
            'The AssociatedBodyTradeName component shall be a sequence of multilingual character strings',
        ]},
    '6.5.5.1/AssociatedBodyAddress': {
        'clause': '6.5.5.1.4', 'title': 'Associated body address', 'kind': 'component',
        'names': ['AssociatedBodyAddress', 'AssosciatedBodyAddress'], 'presence': '0..1',
        'quotes': [
            'The AssosciatedBodyAddress component shall contain the below sub-components:',
        ]},
    '6.5.5.1/AssociatedBodyInformationURI': {
        'clause': '6.5.5.1.5', 'title': 'Associated body information URI', 'kind': 'component',
        'names': ['AssociatedBodyInformationURI', 'AssociatedBodyInformation'], 'presence': '0..1',
        'quotes': [
            'The AssociatedBodyInformation shall be a sequence of multilingual pointers (see clause 6.1.4).',
        ]},
    '6.5.5.1/AssociatedBodyTypeIdentifier': {
        'clause': '6.5.5.1.6', 'title': 'Associated body type identifier', 'kind': 'component',
        'names': ['AssociatedBodyTypeIdentifier'], 'presence': '0..1',
        'quotes': [
            'The AssociatedBodyTypeIdentifier component shall be an indicator expressed as a URI.',
        ]},
    '6.5.5.1/AssociatedBodyInformationExtensions': {
        'clause': '6.5.5.1.7', 'title': 'Associated body information extensions', 'kind': 'component',
        'names': ['AssociatedBodyInformationExtensions'], 'presence': '0..1',
        'quotes': [
            'Sequence of Associated Body extensions whose format is left open.',
        ]},
    '6.6/ServiceInformation': {
        'clause': '6.6.0', 'title': 'Service information', 'kind': 'component',
        'names': ['ServiceInformation'], 'presence': '1',
        'quotes': [
            'The ServiceInformation component provides information about a trusted entity service.',
        ]},
    '6.6.0/StatusRequiredWithHistory': {
        'clause': '6.6.0', 'title': 'ServiceStatus required when history is kept', 'kind': 'rule',
        'names': ['ServiceStatus'], 'presence': 'conditional',
        'quotes': [
            'When the HistoricalInformationPeriod component is present with a non-zero value, the ServiceStatus component shall be present.',
        ]},
    '6.6.1/ServiceTypeIdentifier': {
        'clause': '6.6.1', 'title': 'Service type identifier', 'kind': 'component',
        'names': ['ServiceTypeIdentifier'], 'presence': '0..1',
        'quotes': [
            'The ServiceTypeIdentifier component shall be an indicator expressed as a URI.',
        ]},
    '6.6.2/ServiceName': {
        'clause': '6.6.2', 'title': 'Service name', 'kind': 'component',
        'names': ['ServiceName'], 'presence': '1',
        'quotes': [
            'The ServiceName component shall be a sequence of multilingual character strings (see clause 6.1.4).',
        ]},
    '6.6.3/ServiceDigitalIdentity': {
        'clause': '6.6.3.0', 'title': 'Service digital identity', 'kind': 'component',
        'names': ['ServiceDigitalIdentity'], 'presence': '1',
        'quotes': [
            'The ServiceDigitalIdentity component specifies one or multiple digital identifiers identifying the service with',
        ]},
    '6.6.3.1/X509Certificate': {
        'clause': '6.6.3.1', 'title': 'X.509 certificate', 'kind': 'component',
        'names': ['X509Certificate'], 'presence': '0..n',
        'quotes': [
            'The X509Certificate component shall be a Base64 string.',
        ]},
    '6.6.3.2/X509SubjectName': {
        'clause': '6.6.3.2', 'title': 'X.509 subject name', 'kind': 'component',
        'names': ['X509SubjectName'], 'presence': '0..n',
        'quotes': [
            'The X509SubjectName component shall be a string.',
        ]},
    '6.6.3.3/PublicKeyValue': {
        'clause': '6.6.3.3', 'title': 'Public key value', 'kind': 'component',
        'names': ['PublicKeyValue'], 'presence': '0..n',
        'quotes': [
            'The format of the PublicKeyValue component is left open and is syntax-specific.',
        ]},
    '6.6.3.4/X509SKI': {
        'clause': '6.6.3.4', 'title': 'Subject key identifier', 'kind': 'component',
        'names': ['X509SKI', 'SubjectKeyIdentifier'], 'presence': '0..n',
        'quotes': [
            'The SubjectKeyIdentifier component specifies an identifier of the public key.',
        ]},
    '6.6.3.5/OtherId': {
        'clause': '6.6.3.5', 'title': 'Other identifier', 'kind': 'component',
        'names': ['OtherId'], 'presence': '0..n',
        'quotes': [
            'The format of the OtherId component is left open.',
        ]},
    '6.6.4/ServiceStatus': {
        'clause': '6.6.4', 'title': 'Service current status', 'kind': 'component',
        'names': ['ServiceStatus'], 'presence': '0..1 (see 6.6.0 rule)',
        'quotes': [
            'The ServiceStatus component shall be an identifier expressed as a URI.',
        ]},
    '6.6.5/StatusStartingTime': {
        'clause': '6.6.5', 'title': 'Current status starting date and time', 'kind': 'component',
        'names': ['StatusStartingTime'], 'presence': '0..1',
        'quotes': [
            'The StatusStartingTime component shall be a Date-time value (see clause 6.1.3).',
        ]},
    '6.6.6/SchemeServiceDefinitionURI': {
        'clause': '6.6.6', 'title': 'Scheme service definition URI', 'kind': 'component',
        'names': ['SchemeServiceDefinitionURI'], 'presence': '0..1',
        'quotes': [
            'The SchemeServiceDefinitionURI component shall be a sequence of multilingual pointers (see clause 6.1.4).',
        ]},
    '6.6.7/ServiceSupplyPoints': {
        'clause': '6.6.7', 'title': 'Service supply points', 'kind': 'component',
        'names': ['ServiceSupplyPoints', 'ServiceSupplyPoint'], 'presence': '0..1',
        'quotes': [
            'The ServiceSupplyPoints component shall be a non-empty sequence of URIs, each such URI being optionally',
        ]},
    '6.6.8/TEServiceDefinitionURI': {
        'clause': '6.6.8', 'title': 'TE service definition URI', 'kind': 'component',
        'names': ['TEServiceDefinitionURI', 'ServiceDefinitionURI'], 'presence': '0..1',
        'quotes': [
            'The TEServiceDefinitionURI component shall be a sequence of multilingual pointers (see clause 6.1.4).',
        ]},
    '6.6.9/ServiceInformationExtensions': {
        'clause': '6.6.9.0', 'title': 'Service information extensions', 'kind': 'component',
        'names': ['ServiceInformationExtensions'], 'presence': '0..1',
        'quotes': [
            'The ServiceInformationExtensions component shall be a sequence of ServiceInformationExtension components whose format is left open.',
        ]},
    '6.6.9.1/ServiceUniqueIdentifier': {
        'clause': '6.6.9.1', 'title': 'Service unique identifier extension', 'kind': 'component',
        'names': ['ServiceUniqueIdentifier'], 'presence': '0..1',
        'quotes': [
            'The ServiceUniqueIdentifier component shall be a URI.',
        ]},
    '6.7/ServiceHistoryInstance': {
        'clause': '6.7', 'title': 'Service history instance', 'kind': 'component',
        'names': ['ServiceHistoryInstance'], 'presence': '1..n',
        'quotes': [
            'The ServiceHistoryInstance component provides historical information about a trusted entity service.',
        ]},
}
