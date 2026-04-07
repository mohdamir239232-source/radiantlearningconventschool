from decimal import Decimal, InvalidOperation

from django import forms

from .models import AcademicSession, ClassModel, Student
from transport.models import VehicleRoute


INDIAN_STATES = [
    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa',
    'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
    'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland',
    'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura',
    'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi'
]

STATE_DISTRICT_MAP = {
    'Andhra Pradesh': [
        'Alluri Sitharama Raju', 'Anakapalli', 'Anantapuramu', 'Annamayya', 'Bapatla', 'Chittoor',
        'Dr. B.R. Ambedkar Konaseema', 'East Godavari', 'Eluru', 'Guntur', 'Kakinada', 'Krishna',
        'Kurnool', 'Nandyal', 'NTR', 'Palnadu', 'Parvathipuram Manyam', 'Prakasam', 'SPSR Nellore',
        'Sri Sathya Sai', 'Srikakulam', 'Tirupati', 'Visakhapatnam', 'Vizianagaram',
        'West Godavari', 'YSR Kadapa'
    ],
    'Arunachal Pradesh': [
        'Anjaw', 'Changlang', 'Dibang Valley', 'East Kameng', 'East Siang', 'Kamle', 'Kra Daadi',
        'Kurung Kumey', 'Leparada', 'Lohit', 'Longding', 'Lower Dibang Valley', 'Lower Siang',
        'Lower Subansiri', 'Namsai', 'Pakke Kessang', 'Papum Pare', 'Shi Yomi', 'Siang', 'Tawang',
        'Tirap', 'Upper Siang', 'Upper Subansiri', 'West Kameng', 'West Siang'
    ],
    'Assam': [
        'Baksa', 'Bajali', 'Barpeta', 'Biswanath', 'Bongaigaon', 'Cachar', 'Charaideo', 'Chirang',
        'Darrang', 'Dhemaji', 'Dhubri', 'Dibrugarh', 'Dima Hasao', 'Goalpara', 'Golaghat', 'Hailakandi',
        'Hojai', 'Jorhat', 'Kamrup', 'Kamrup Metropolitan', 'Karbi Anglong', 'Kokrajhar', 'Lakhimpur',
        'Majuli', 'Morigaon', 'Nagaon', 'Nalbari', 'Sivasagar', 'Sonitpur', 'South Salmara-Mankachar',
        'Tamulpur', 'Tinsukia', 'Udalguri', 'West Karbi Anglong'
    ],
    'Bihar': [
        'Araria', 'Arwal', 'Aurangabad', 'Banka', 'Begusarai', 'Bhagalpur', 'Bhojpur', 'Buxar',
        'Darbhanga', 'East Champaran', 'Gaya', 'Gopalganj', 'Jamui', 'Jehanabad', 'Kaimur', 'Katihar',
        'Khagaria', 'Kishanganj', 'Lakhisarai', 'Madhepura', 'Madhubani', 'Munger', 'Muzaffarpur',
        'Nalanda', 'Nawada', 'Patna', 'Purnia', 'Rohtas', 'Saharsa', 'Samastipur', 'Saran',
        'Sheikhpura', 'Sheohar', 'Sitamarhi', 'Siwan', 'Supaul', 'Vaishali', 'West Champaran'
    ],
    'Chhattisgarh': [
        'Balod', 'Baloda Bazar', 'Balrampur', 'Bastar', 'Bemetara', 'Bijapur', 'Bilaspur',
        'Dantewada', 'Dhamtari', 'Durg', 'Gariaband', 'Gaurela-Pendra-Marwahi', 'Janjgir-Champa',
        'Jashpur', 'Kabirdham', 'Kanker', 'Khairagarh-Chhuikhadan-Gandai', 'Kondagaon', 'Korba',
        'Koriya', 'Mahasamund', 'Manendragarh-Chirmiri-Bharatpur', 'Mohla-Manpur-Ambagarh Chowki',
        'Mungeli', 'Narayanpur', 'Raigarh', 'Raipur', 'Rajnandgaon', 'Sakti', 'Sarangarh-Bilaigarh',
        'Sukma', 'Surajpur', 'Surguja'
    ],
    'Goa': ['North Goa', 'South Goa'],
    'Gujarat': [
        'Ahmedabad', 'Amreli', 'Anand', 'Aravalli', 'Banaskantha', 'Bharuch', 'Bhavnagar', 'Botad',
        'Chhota Udaipur', 'Dahod', 'Dang', 'Devbhoomi Dwarka', 'Gandhinagar', 'Gir Somnath', 'Jamnagar',
        'Junagadh', 'Kheda', 'Kutch', 'Mahisagar', 'Mehsana', 'Morbi', 'Narmada', 'Navsari', 'Panchmahal',
        'Patan', 'Porbandar', 'Rajkot', 'Sabarkantha', 'Surat', 'Surendranagar', 'Tapi', 'Vadodara',
        'Valsad'
    ],
    'Haryana': [
        'Ambala', 'Bhiwani', 'Charkhi Dadri', 'Faridabad', 'Fatehabad', 'Gurugram', 'Hisar', 'Jhajjar',
        'Jind', 'Kaithal', 'Karnal', 'Kurukshetra', 'Mahendragarh', 'Nuh', 'Palwal', 'Panchkula',
        'Panipat', 'Rewari', 'Rohtak', 'Sirsa', 'Sonipat', 'Yamunanagar'
    ],
    'Himachal Pradesh': [
        'Bilaspur', 'Chamba', 'Hamirpur', 'Kangra', 'Kinnaur', 'Kullu', 'Lahaul and Spiti',
        'Mandi', 'Shimla', 'Sirmaur', 'Solan', 'Una'
    ],
    'Jharkhand': [
        'Bokaro', 'Chatra', 'Deoghar', 'Dhanbad', 'Dumka', 'East Singhbhum', 'Garhwa', 'Giridih',
        'Godda', 'Gumla', 'Hazaribagh', 'Jamtara', 'Khunti', 'Koderma', 'Latehar', 'Lohardaga',
        'Pakur', 'Palamu', 'Ramgarh', 'Ranchi', 'Sahibganj', 'Saraikela-Kharsawan', 'Simdega', 'West Singhbhum'
    ],
    'Karnataka': [
        'Bagalkot', 'Ballari', 'Belagavi', 'Bengaluru Rural', 'Bengaluru Urban', 'Bidar', 'Chamarajanagar',
        'Chikkaballapur', 'Chikkamagaluru', 'Chitradurga', 'Dakshina Kannada', 'Davanagere', 'Dharwad',
        'Gadag', 'Hassan', 'Haveri', 'Kalaburagi', 'Kodagu', 'Kolar', 'Koppal', 'Mandya', 'Mysuru',
        'Raichur', 'Ramanagara', 'Shivamogga', 'Tumakuru', 'Udupi', 'Uttara Kannada', 'Vijayapura',
        'Yadgir'
    ],
    'Kerala': [
        'Alappuzha', 'Ernakulam', 'Idukki', 'Kannur', 'Kasaragod', 'Kollam', 'Kottayam', 'Kozhikode',
        'Malappuram', 'Palakkad', 'Pathanamthitta', 'Thiruvananthapuram', 'Thrissur', 'Wayanad'
    ],
    'Madhya Pradesh': [
        'Agar Malwa', 'Alirajpur', 'Anuppur', 'Ashoknagar', 'Balaghat', 'Barwani', 'Betul', 'Bhind',
        'Bhopal', 'Burhanpur', 'Chhatarpur', 'Chhindwara', 'Damoh', 'Datia', 'Dewas', 'Dhar',
        'Dindori', 'Guna', 'Gwalior', 'Harda', 'Narmadapuram', 'Indore', 'Jabalpur', 'Jhabua',
        'Katni', 'Khandwa', 'Khargone', 'Mandla', 'Mandsaur', 'Morena', 'Narsinghpur', 'Neemuch',
        'Niwari', 'Panna', 'Raisen', 'Rajgarh', 'Ratlam', 'Rewa', 'Sagar', 'Satna', 'Sehore',
        'Seoni', 'Shahdol', 'Shajapur', 'Sheopur', 'Shivpuri', 'Sidhi', 'Singrauli', 'Tikamgarh',
        'Ujjain', 'Umaria', 'Vidisha'
    ],
    'Maharashtra': [
        'Ahmednagar', 'Akola', 'Amravati', 'Aurangabad', 'Beed', 'Bhandara', 'Buldhana', 'Chandrapur',
        'Dhule', 'Gadchiroli', 'Gondia', 'Hingoli', 'Jalgaon', 'Jalna', 'Kolhapur', 'Latur', 'Mumbai City',
        'Mumbai Suburban', 'Nagpur', 'Nanded', 'Nandurbar', 'Nashik', 'Osmanabad', 'Palghar', 'Parbhani',
        'Pune', 'Raigad', 'Ratnagiri', 'Sangli', 'Satara', 'Sindhudurg', 'Solapur', 'Thane', 'Wardha',
        'Washim', 'Yavatmal'
    ],
    'Manipur': [
        'Bishnupur', 'Chandel', 'Churachandpur', 'Imphal East', 'Imphal West', 'Jiribam', 'Kakching',
        'Kamjong', 'Kangpokpi', 'Noney', 'Pherzawl', 'Senapati', 'Tamenglong', 'Tengnoupal', 'Thoubal', 'Ukhrul'
    ],
    'Meghalaya': [
        'East Garo Hills', 'East Jaintia Hills', 'East Khasi Hills', 'North Garo Hills',
        'Ri-Bhoi', 'South Garo Hills', 'South West Garo Hills', 'South West Khasi Hills',
        'West Garo Hills', 'West Jaintia Hills', 'West Khasi Hills'
    ],
    'Mizoram': ['Aizawl', 'Champhai', 'Hnahthial', 'Khawzawl', 'Kolasib', 'Lawngtlai', 'Lunglei', 'Mamit', 'Saiha', 'Saitual', 'Serchhip'],
    'Nagaland': ['Chumoukedima', 'Dimapur', 'Kiphire', 'Kohima', 'Longleng', 'Mokokchung', 'Mon', 'Niuland', 'Noklak', 'Peren', 'Phek', 'Shamator', 'Tuensang', 'Tseminyu', 'Wokha', 'Zunheboto'],
    'Odisha': [
        'Angul', 'Balangir', 'Balasore', 'Bargarh', 'Bhadrak', 'Boudh', 'Cuttack', 'Deogarh', 'Dhenkanal',
        'Gajapati', 'Ganjam', 'Jagatsinghpur', 'Jajpur', 'Jharsuguda', 'Kalahandi', 'Kandhamal', 'Kendrapara',
        'Kendujhar', 'Khordha', 'Koraput', 'Malkangiri', 'Mayurbhanj', 'Nabarangpur', 'Nayagarh', 'Nuapada',
        'Puri', 'Rayagada', 'Sambalpur', 'Subarnapur', 'Sundargarh'
    ],
    'Punjab': [
        'Amritsar', 'Barnala', 'Bathinda', 'Faridkot', 'Fatehgarh Sahib', 'Fazilka', 'Firozpur',
        'Gurdaspur', 'Hoshiarpur', 'Jalandhar', 'Kapurthala', 'Ludhiana', 'Malerkotla', 'Mansa',
        'Moga', 'Pathankot', 'Patiala', 'Rupnagar', 'S.A.S. Nagar', 'Sangrur', 'Sri Muktsar Sahib', 'Tarn Taran'
    ],
    'Rajasthan': [
        'Ajmer', 'Alwar', 'Anupgarh', 'Balotra', 'Banswara', 'Baran', 'Barmer', 'Beawar', 'Bharatpur',
        'Bhilwara', 'Bikaner', 'Bundi', 'Chittorgarh', 'Churu', 'Dausa', 'Deeg', 'Dholpur', 'Didwana-Kuchaman',
        'Dungarpur', 'Hanumangarh', 'Jaipur', 'Jaisalmer', 'Jalore', 'Jhalawar', 'Jhunjhunu', 'Jodhpur',
        'Karauli', 'Kekri', 'Khairthal-Tijara', 'Kota', 'Kotputli-Behror', 'Nagaur', 'Pali', 'Phalodi',
        'Pratapgarh', 'Rajsamand', 'Salumber', 'Sanchore', 'Sawai Madhopur', 'Shahpura', 'Sikar', 'Sirohi',
        'Sri Ganganagar', 'Tonk', 'Udaipur'
    ],
    'Sikkim': ['Gangtok', 'Namchi', 'Gyalshing', 'Mangan', 'Pakyong'],
    'Tamil Nadu': [
        'Ariyalur', 'Chengalpattu', 'Chennai', 'Coimbatore', 'Cuddalore', 'Dharmapuri', 'Dindigul',
        'Erode', 'Kallakurichi', 'Kancheepuram', 'Kanyakumari', 'Karur', 'Krishnagiri', 'Madurai',
        'Mayiladuthurai', 'Nagapattinam', 'Namakkal', 'Nilgiris', 'Perambalur', 'Pudukkottai', 'Ramanathapuram',
        'Ranipet', 'Salem', 'Sivaganga', 'Tenkasi', 'Thanjavur', 'Theni', 'Thoothukudi', 'Tiruchirappalli',
        'Tirunelveli', 'Tirupathur', 'Tiruppur', 'Tiruvallur', 'Tiruvannamalai', 'Tiruvarur', 'Vellore',
        'Viluppuram', 'Virudhunagar'
    ],
    'Telangana': [
        'Adilabad', 'Bhadradri Kothagudem', 'Hanumakonda', 'Hyderabad', 'Jagtial', 'Jangaon',
        'Jayashankar Bhupalpally', 'Jogulamba Gadwal', 'Kamareddy', 'Karimnagar', 'Khammam',
        'Komaram Bheem Asifabad', 'Mahabubabad', 'Mahabubnagar', 'Mancherial', 'Medak', 'Medchal-Malkajgiri',
        'Mulugu', 'Nagarkurnool', 'Nalgonda', 'Narayanpet', 'Nirmal', 'Nizamabad', 'Peddapalli',
        'Rajanna Sircilla', 'Ranga Reddy', 'Sangareddy', 'Siddipet', 'Suryapet', 'Vikarabad',
        'Wanaparthy', 'Warangal', 'Yadadri Bhuvanagiri'
    ],
    'Tripura': ['Dhalai', 'Gomati', 'Khowai', 'North Tripura', 'Sepahijala', 'South Tripura', 'Unakoti', 'West Tripura'],
    'Uttar Pradesh': [
        'Agra', 'Aligarh', 'Ambedkar Nagar', 'Amethi', 'Amroha', 'Auraiya', 'Ayodhya', 'Azamgarh',
        'Baghpat', 'Bahraich', 'Ballia', 'Balrampur', 'Banda', 'Barabanki', 'Bareilly', 'Basti', 'Bhadohi',
        'Bijnor', 'Budaun', 'Bulandshahr', 'Chandauli', 'Chitrakoot', 'Deoria', 'Etah', 'Etawah',
        'Farrukhabad', 'Fatehpur', 'Firozabad', 'Gautam Buddha Nagar', 'Ghaziabad', 'Ghazipur', 'Gonda',
        'Gorakhpur', 'Hamirpur', 'Hapur', 'Hardoi', 'Hathras', 'Jalaun', 'Jaunpur', 'Jhansi', 'Kannauj',
        'Kanpur Dehat', 'Kanpur Nagar', 'Kasganj', 'Kaushambi', 'Kheri', 'Kushinagar', 'Lalitpur',
        'Lucknow', 'Maharajganj', 'Mahoba', 'Mainpuri', 'Mathura', 'Mau', 'Meerut', 'Mirzapur', 'Moradabad',
        'Muzaffarnagar', 'Pilibhit', 'Pratapgarh', 'Prayagraj', 'Raebareli', 'Rampur', 'Saharanpur',
        'Sambhal', 'Sant Kabir Nagar', 'Shahjahanpur', 'Shamli', 'Shravasti', 'Siddharthnagar', 'Sitapur',
        'Sonbhadra', 'Sultanpur', 'Unnao', 'Varanasi'
    ],
    'Uttarakhand': ['Almora', 'Bageshwar', 'Chamoli', 'Champawat', 'Dehradun', 'Haridwar', 'Nainital', 'Pauri Garhwal', 'Pithoragarh', 'Rudraprayag', 'Tehri Garhwal', 'Udham Singh Nagar', 'Uttarkashi'],
    'West Bengal': [
        'Alipurduar', 'Bankura', 'Birbhum', 'Cooch Behar', 'Dakshin Dinajpur', 'Darjeeling', 'Hooghly',
        'Howrah', 'Jalpaiguri', 'Jhargram', 'Kalimpong', 'Kolkata', 'Malda', 'Murshidabad', 'Nadia',
        'North 24 Parganas', 'Paschim Bardhaman', 'Paschim Medinipur', 'Purba Bardhaman',
        'Purba Medinipur', 'Purulia', 'South 24 Parganas', 'Uttar Dinajpur'
    ],
    'Delhi': ['Central Delhi', 'East Delhi', 'New Delhi', 'North Delhi', 'North East Delhi', 'North West Delhi', 'Shahdara', 'South Delhi', 'South East Delhi', 'South West Delhi', 'West Delhi'],
}

ALL_DISTRICTS = sorted({district for districts in STATE_DISTRICT_MAP.values() for district in districts})


class StudentAdmissionForm(forms.ModelForm):
    gender = forms.ChoiceField(choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    category = forms.ChoiceField(choices=[('', 'Select Category'), ('General', 'General'), ('OBC', 'OBC'), ('SC', 'SC'), ('ST', 'ST'), ('EWS', 'EWS')])
    fee_category = forms.ChoiceField(choices=[('', 'Select Fee Category'), ('Regular', 'Regular'), ('RTE', 'RTE'), ('Scholarship', 'Scholarship')])
    student_status = forms.ChoiceField(choices=[('', 'Select New/Old'), ('New', 'New'), ('Old', 'Old')])
    state = forms.ChoiceField(choices=[('', 'Select State')] + [(s, s) for s in INDIAN_STATES], required=False)
    district = forms.ChoiceField(choices=[('', 'Select District')], required=False)
    previous_class = forms.ChoiceField(
        choices=[('', 'Select Class')] + [(str(i), f'Class {i}') for i in range(1, 13)],
        required=False,
    )
    transport_required = forms.ChoiceField(choices=[('No', 'No'), ('Yes', 'Yes')], required=False)
    transport_village = forms.ChoiceField(required=False)
    transport_amount = forms.DecimalField(required=False, decimal_places=2, max_digits=8)

    class Meta:
        model = Student
        fields = [
            'admission_number',
            'name',
            'dob',
            'pen_number',
            'student_class',
            'section',
            'admission_date',
            'gender',
            'category',
            'fee_category',
            'student_status',
            'aadhar_number',
            'address',
            'state',
            'district',
            'pin_code',
            'nationality',
            'father_name',
            'mother_name',
            'local_guardian',
            'father_occupation',
            'mother_occupation',
            'father_qualification',
            'mother_qualification',
            'father_aadhar',
            'mother_aadhar',
            'father_mobile',
            'mother_mobile',
            'last_school_name',
            'previous_class',
            'last_school_address',
            'apaar_id',
            'parents_detail',
            'contact_detail',
            'photo',
            'roll_no',
            'session',
            'transport_required',
            'transport_route',
            'transport_village',
            'transport_amount',
        ]
        widgets = {
            'admission_number': forms.TextInput(attrs={'readonly': 'readonly'}),
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'admission_date': forms.DateInput(attrs={'type': 'date'}),
            'parents_detail': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'last_school_address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial['admission_number'] = Student.get_next_admission_number()
        self.fields['admission_number'].required = False
        self.fields['roll_no'].required = False
        self.fields['roll_no'].widget.attrs['readonly'] = 'readonly'
        self.fields['roll_no'].widget.attrs['placeholder'] = 'Auto-generated'

        selected_state = self.data.get('state') or self.initial.get('state') or getattr(self.instance, 'state', None)
        district_choices = [('', 'Select District')]
        if selected_state in STATE_DISTRICT_MAP:
            district_choices.extend((district, district) for district in STATE_DISTRICT_MAP[selected_state])

        current_district = self.data.get('district') or self.initial.get('district') or getattr(self.instance, 'district', None)
        if current_district and current_district not in [d[0] for d in district_choices]:
            district_choices.append((current_district, current_district))
        self.fields['district'].choices = district_choices

        class_names = list(
            ClassModel.objects.filter(is_active=True)
            .order_by('name')
            .values_list('name', flat=True)
            .distinct()
        )
        class_choices = [('', 'Select Class')] + [(name, name) for name in class_names]
        if not class_names:
            class_choices = [('', 'Select Class')] + [(str(i), f'Class {i}') for i in range(1, 13)]

        self.fields['student_class'].widget = forms.Select(choices=class_choices)

        selected_class = self.data.get('student_class') or self.initial.get('student_class') or getattr(self.instance, 'student_class', None)
        section_values = list(
            ClassModel.objects.filter(is_active=True, name=selected_class)
            .exclude(section__isnull=True)
            .exclude(section__exact='')
            .values_list('section', flat=True)
            .distinct()
        ) if selected_class else []
        section_choices = [('', 'Select Section')] + [(value, value) for value in section_values]
        if not section_values:
            section_choices = [('', 'Select Section'), ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]
        self.fields['section'].widget = forms.Select(choices=section_choices)

        self.fields['session'].queryset = AcademicSession.objects.filter(is_active=True).order_by('-id')
        self.fields['transport_route'].queryset = VehicleRoute.objects.filter(is_active=True).order_by('route_name')

        selected_route = self.data.get('transport_route') or self.initial.get('transport_route')
        if not selected_route and getattr(self.instance, 'transport_route_id', None):
            selected_route = self.instance.transport_route_id

        village_choices = [('', 'Select transport village')]
        if selected_route:
            try:
                route = VehicleRoute.objects.get(pk=selected_route, is_active=True)
                route_villages = route.get_stops_list()
                village_choices.extend((v, v) for v in route_villages)
            except (VehicleRoute.DoesNotExist, ValueError, TypeError):
                pass

        if len(village_choices) == 1:
            villages = set()
            for route in VehicleRoute.objects.filter(is_active=True):
                for stop in route.get_stops_list():
                    villages.add(stop)
            village_choices.extend((v, v) for v in sorted(villages))

        self.fields['transport_village'].choices = village_choices
        self.fields['transport_amount'].widget.attrs['readonly'] = 'readonly'
        if 'photo' in self.fields:
            self.fields['photo'].widget.attrs['accept'] = 'image/*'

    def clean_transport_required(self):
        value = self.cleaned_data.get('transport_required')
        return value == 'Yes'

    def _blank_to_none(self, key):
        value = self.cleaned_data.get(key)
        return value if value not in ('', None) else None

    def clean_pen_number(self):
        return self._blank_to_none('pen_number')

    def clean_apaar_id(self):
        return self._blank_to_none('apaar_id')

    def clean_aadhar_number(self):
        return self._blank_to_none('aadhar_number')

    def clean(self):
        cleaned_data = super().clean()
        route = cleaned_data.get('transport_route')
        village = cleaned_data.get('transport_village')
        transport_required = cleaned_data.get('transport_required')
        selected_state = cleaned_data.get('state')
        district = cleaned_data.get('district')

        if selected_state and not district:
            self.add_error('district', 'District is required when a state is selected.')

        if selected_state and district:
            allowed_districts = STATE_DISTRICT_MAP.get(selected_state, [])
            if district not in allowed_districts:
                self.add_error('district', 'Please select district from selected state only.')

        if transport_required and not route:
            self.add_error('transport_route', 'Please select route when transport is required.')

        if route:
            village_fare = None
            if village:
                for item in route.get_village_fare_list():
                    if item.get('village') == village and item.get('fare') not in (None, ''):
                        try:
                            village_fare = Decimal(str(item.get('fare')))
                        except (InvalidOperation, TypeError, ValueError):
                            village_fare = None
                        break

            cleaned_data['transport_amount'] = village_fare if village_fare is not None else route.fare_amount
        else:
            cleaned_data['transport_amount'] = None

        return cleaned_data


class StudentProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'name',
            'dob',
            'gender',
            'category',
            'fee_category',
            'student_status',
            'pen_number',
            'aadhar_number',
            'apaar_id',
            'contact_detail',
            'address',
            'state',
            'district',
            'pin_code',
            'nationality',
            'father_name',
            'mother_name',
            'local_guardian',
            'father_mobile',
            'mother_mobile',
            'student_class',
            'section',
            'session',
            'transport_required',
            'transport_route',
            'transport_village',
            'photo',
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        class_names = list(
            ClassModel.objects.filter(is_active=True)
            .order_by('name')
            .values_list('name', flat=True)
            .distinct()
        )
        class_choices = [('', 'Select Class')] + [(name, name) for name in class_names]
        if not class_names:
            class_choices = [('', 'Select Class')] + [(str(i), f'Class {i}') for i in range(1, 13)]
        self.fields['student_class'].widget = forms.Select(choices=class_choices)

        selected_class = self.data.get('student_class') or getattr(self.instance, 'student_class', None)
        section_values = list(
            ClassModel.objects.filter(is_active=True, name=selected_class)
            .exclude(section__isnull=True)
            .exclude(section__exact='')
            .values_list('section', flat=True)
            .distinct()
        ) if selected_class else []
        section_choices = [('', 'Select Section')] + [(value, value) for value in section_values]
        if not section_values:
            section_choices = [('', 'Select Section'), ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]
        self.fields['section'].widget = forms.Select(choices=section_choices)

        self.fields['session'].queryset = AcademicSession.objects.filter(is_active=True).order_by('-id')
        self.fields['transport_route'].queryset = VehicleRoute.objects.filter(is_active=True).order_by('route_name')
        self.fields['photo'].widget.attrs['accept'] = 'image/*'
