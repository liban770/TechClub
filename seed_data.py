import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techclub_core.settings')
django.setup()

from accounts.models import User, UserRole
from applications.models import Application, ApplicationStatus, ReferralSource, ExperienceLevel, DisciplineCategory, NotificationLog
from members.models import MemberProfile, Skill
from events.models import Event, EventCategory, EventStatus, EventRegistration
from meetings.models import Meeting, MeetingPurpose, MeetingStatus, MeetingParticipant
from announcements.models import Announcement, AnnouncementCategory, AnnouncementAudience, PublicationStatus

def run_seed():
    print("Clearing old data or populating seed...")

    # 1. Create Lead Admin Organizer
    admin_user, created = User.objects.get_or_create(
        email='jamaal@techclub.so',
        defaults={
            'username': 'jamaal_k',
            'first_name': 'Jamaal',
            'last_name': 'K.',
            'role': UserRole.ORGANIZER,
            'is_staff': True,
            'is_superuser': True,
        }
    )
    admin_user.set_password('adminpass123')
    admin_user.save()
    print("Organizer user ready: jamaal@techclub.so (password: adminpass123)")

    # 2. Seed Skills
    skills_data = [
        ("Python", "Backend"), ("Django", "Backend"), ("PostgreSQL", "Database"),
        ("React", "Frontend"), ("TypeScript", "Frontend"), ("Next.js", "Frontend"),
        ("Rust", "Systems"), ("Go", "Backend"), ("Docker", "Cloud & DevOps"),
        ("Kubernetes", "Cloud & DevOps"), ("AWS", "Cloud & DevOps"),
        ("Figma", "Design"), ("UI/UX Design", "Design"), ("Product Design", "Design"),
        ("Machine Learning", "Data & AI"), ("FastAPI", "Backend"), ("Flutter", "Mobile"),
        ("Cybersecurity", "Security"), ("System Architecture", "Architecture")
    ]
    skill_objects = {}
    for name, cat in skills_data:
        s, _ = Skill.objects.get_or_create(name=name, defaults={'category': cat})
        skill_objects[name] = s

    # 3. Create Sample Approved Members & Profiles
    members_seed = [
        {
            'email': 'guled.abdi@telesom.so',
            'username': 'guled_abdi',
            'first_name': 'Guled',
            'last_name': 'Abdi',
            'title': 'Senior Full Stack Engineer & Cloud Architect',
            'org': 'Telesom Tech Labs',
            'discipline': DisciplineCategory.SOFTWARE_ENG,
            'exp': ExperienceLevel.SENIOR,
            'bio': 'Software engineer and system architect with 6+ years shipping high-throughput distributed systems, fintech gateways, and mobile APIs in East Africa. Passionate about mentoring the next generation of engineers in Hargeisa.',
            'skills': ['Python', 'Django', 'Rust', 'Docker', 'PostgreSQL', 'System Architecture'],
            'is_mentor': True,
            'github': 'https://github.com',
            'linkedin': 'https://linkedin.com',
            'avatar': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80',
            'cohort': 'Cohort #1'
        },
        {
            'email': 'nimco.farhan@designlab.so',
            'username': 'nimco_farhan',
            'first_name': 'Nimco',
            'last_name': 'Farhan',
            'title': 'Lead Product & UI/UX Designer',
            'org': 'Hargeisa Digital Collective',
            'discipline': DisciplineCategory.DESIGN,
            'exp': ExperienceLevel.MID,
            'bio': 'Designing human-centered digital experiences for mobile money and regional fintech. Advocate for women in technology and design-thinking sprints.',
            'skills': ['Figma', 'UI/UX Design', 'Product Design', 'React'],
            'is_mentor': True,
            'github': '',
            'linkedin': 'https://linkedin.com',
            'avatar': 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=400&q=80',
            'cohort': 'Cohort #2'
        },
        {
            'email': 'mohamed.khalif@builder.so',
            'username': 'mohamed_khalif',
            'first_name': 'Mohamed',
            'last_name': 'Khalif',
            'title': 'Backend Developer & API Specialist',
            'org': 'Dahabshiil Innovation Unit',
            'discipline': DisciplineCategory.SOFTWARE_ENG,
            'exp': ExperienceLevel.MID,
            'bio': 'Building robust fintech microservices and cloud payment integrations. Community contributor and co-organizer of weekly code sessions.',
            'skills': ['Go', 'PostgreSQL', 'Docker', 'Kubernetes', 'FastAPI'],
            'is_mentor': False,
            'github': 'https://github.com',
            'linkedin': 'https://linkedin.com',
            'avatar': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80',
            'cohort': 'Cohort #2'
        },
        {
            'email': 'fathia.rashid@aihorn.so',
            'username': 'fathia_rashid',
            'first_name': 'Fathia',
            'last_name': 'Rashid',
            'title': 'Machine Learning & Data Specialist',
            'org': 'University of Hargeisa Research Hub',
            'discipline': DisciplineCategory.AI_DATA,
            'exp': ExperienceLevel.JUNIOR,
            'bio': 'Passionate about NLP for low-resource Somali language modeling and computer vision datasets. Organizing data science study groups in Somaliland.',
            'skills': ['Python', 'Machine Learning', 'FastAPI', 'PostgreSQL'],
            'is_mentor': False,
            'github': 'https://github.com',
            'linkedin': 'https://linkedin.com',
            'avatar': 'https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?auto=format&fit=crop&w=400&q=80',
            'cohort': 'Cohort #3'
        },
        {
            'email': 'hamse.abdirahman@cloudops.so',
            'username': 'hamse_ops',
            'first_name': 'Hamse',
            'last_name': 'Abdirahman',
            'title': 'DevOps & Infrastructure Engineer',
            'org': 'SomCable Cloud Systems',
            'discipline': DisciplineCategory.DEVOPS,
            'exp': ExperienceLevel.SENIOR,
            'bio': '10+ years managing regional optic fibre networks, hybrid cloud infrastructure, and Linux sysadmin security.',
            'skills': ['AWS', 'Docker', 'Kubernetes', 'Cybersecurity', 'Go'],
            'is_mentor': True,
            'github': 'https://github.com',
            'linkedin': 'https://linkedin.com',
            'avatar': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80',
            'cohort': 'Cohort #1'
        }
    ]

    for m in members_seed:
        u, _ = User.objects.get_or_create(
            email=m['email'],
            defaults={
                'username': m['username'],
                'first_name': m['first_name'],
                'last_name': m['last_name'],
                'role': UserRole.MEMBER,
                'is_active': True,
            }
        )
        u.set_password('memberpass123')
        u.save()

        profile, _ = MemberProfile.objects.get_or_create(
            user=u,
            defaults={
                'full_name': f"{m['first_name']} {m['last_name']}",
                'professional_title': m['title'],
                'organization': m['org'],
                'discipline': m['discipline'],
                'experience_level': m['exp'],
                'bio': m['bio'],
                'is_mentor': m['is_mentor'],
                'cohort': m['cohort'],
                'github_url': m['github'],
                'linkedin_url': m['linkedin'],
                'avatar_url': m['avatar'],
                'profile_visibility': 'PUBLIC',
                'show_email': False,
            }
        )
        for s_name in m['skills']:
            if s_name in skill_objects:
                profile.skills.add(skill_objects[s_name])

    print("Created 5 sample verified community members with profiles.")

    # 4. Create Applications in various statuses
    applications_seed = [
        {
            'full_name': 'Ayanle Muse Warsame',
            'email': 'ayanle.warsame@techstart.so',
            'phone': '+252 63 4412345',
            'city': 'Hargeisa',
            'role': 'Junior Frontend Developer',
            'category': DisciplineCategory.SOFTWARE_ENG,
            'org': 'Amoud University Alum',
            'exp': ExperienceLevel.JUNIOR,
            'skills': 'React, Tailwind CSS, JavaScript, Git',
            'summary': 'Recent computer science graduate with two completed client websites. Excited to join a structured peer group and find a senior frontend mentor.',
            'interests': 'Finding a mentor, Collaborating on projects, Participating in technology events',
            'source': ReferralSource.WHATSAPP,
            'github': 'https://github.com/ayanle-code',
            'linkedin': 'https://linkedin.com/in/ayanle-w',
            'status': ApplicationStatus.PENDING,
            'notes': ''
        },
        {
            'full_name': 'Khadra Ismail Duale',
            'email': 'khadra.duale@hornsecurity.so',
            'phone': '+252 63 4298765',
            'city': 'Hargeisa',
            'role': 'Cybersecurity Analyst',
            'category': DisciplineCategory.CYBERSECURITY,
            'org': 'National Bank Information Security',
            'exp': ExperienceLevel.MID,
            'skills': 'Penetration Testing, Network Defense, Python, Linux',
            'summary': 'Working in defensive security operations for banking systems. Keen to deliver workshops on secure authentication for local startups.',
            'interests': 'Sharing knowledge, Professional networking, Tech events',
            'source': ReferralSource.LINKEDIN,
            'github': 'https://github.com/khadra-sec',
            'linkedin': 'https://linkedin.com/in/khadra-duale',
            'status': ApplicationStatus.PENDING,
            'notes': 'Strong background, could co-host our next security lab.'
        },
        {
            'full_name': 'Suleiman Jama Hassan',
            'email': 'suleiman.jama@startup.so',
            'phone': '+252 63 4771122',
            'city': 'Borama',
            'role': 'Co-Founder & CTO',
            'category': DisciplineCategory.FOUNDERS,
            'org': 'GeelPay Technologies',
            'exp': ExperienceLevel.SENIOR,
            'skills': 'Fintech, Python, PostgreSQL, System Design',
            'summary': 'Building digital merchant solutions for Somaliland retailers. Looking for senior collaborators and talent to recruit.',
            'interests': 'Collaborating on projects, Discovering career opportunities, Professional networking',
            'source': ReferralSource.FRIEND,
            'github': 'https://github.com/suleiman-jama',
            'linkedin': 'https://linkedin.com/in/suleiman-jama',
            'status': ApplicationStatus.PENDING,
            'notes': ''
        },
        {
            'full_name': 'Hodan Osman Barre',
            'email': 'hodan.barre@student.so',
            'phone': '+252 63 4905544',
            'city': 'Hargeisa',
            'role': 'Aspiring UI/UX Designer',
            'category': DisciplineCategory.DESIGN,
            'org': 'Golis University',
            'exp': ExperienceLevel.JUNIOR,
            'skills': 'Figma, Wireframing, User Research',
            'summary': 'Self-taught UI designer building case studies for local delivery apps. Want to learn best practices and design systems from senior leads.',
            'interests': 'Learning from experienced professionals, Finding a mentor',
            'source': ReferralSource.TIKTOK,
            'github': '',
            'linkedin': 'https://linkedin.com/in/hodan-barre',
            'status': ApplicationStatus.WAITLISTED,
            'notes': 'Portfolio is promising. Placed on waitlist for Cohort #3 design track opening.'
        },
        {
            'full_name': 'Barkhad Yasin Ahmed',
            'email': 'barkhad.yasin@freelance.so',
            'phone': '+252 63 4118899',
            'city': 'Hargeisa',
            'role': 'Full Stack Developer',
            'category': DisciplineCategory.SOFTWARE_ENG,
            'org': 'Independent Freelancer',
            'exp': ExperienceLevel.MID,
            'skills': 'Node.js, Express, React, MongoDB',
            'summary': 'Freelance builder shipping client apps. Want to connect with fellow builders and contribute to open source initiatives in Somaliland.',
            'interests': 'Professional networking, Collaborating on projects',
            'source': ReferralSource.UNIVERSITY,
            'github': 'https://github.com/barkhad-y',
            'linkedin': 'https://linkedin.com/in/barkhad-y',
            'status': ApplicationStatus.APPROVED,
            'notes': 'Approved for Cohort #2. Account activation token sent.'
        }
    ]

    for app in applications_seed:
        Application.objects.get_or_create(
            email=app['email'],
            defaults={
                'full_name': app['full_name'],
                'phone': app['phone'],
                'city': app['city'],
                'current_role': app['role'],
                'professional_category': app['category'],
                'organization': app['org'],
                'experience_level': app['exp'],
                'skills': app['skills'],
                'profile_summary': app['summary'],
                'interests': app['interests'],
                'referral_source': app['source'],
                'github_url': app['github'],
                'linkedin_url': app['linkedin'],
                'status': app['status'],
                'organizer_notes': app['notes'],
                'reviewed_by': admin_user if app['status'] != ApplicationStatus.PENDING else None,
                'reviewed_at': timezone.now() if app['status'] != ApplicationStatus.PENDING else None
            }
        )

    print("Created 5 sample applications across Pending, Waitlisted, and Approved states.")

    # 5. Create Events
    now = timezone.now()
    events_seed = [
        {
            'title': 'Hargeisa Web3, Cloud & Distributed Systems Meetup',
            'desc': 'Join senior software architects and cloud builders from across Somaliland to explore microservices at scale, regional telecom payment APIs, and real-world event-driven architecture.',
            'cat': EventCategory.MEETUP,
            'start': now + timedelta(days=3, hours=2),
            'end': now + timedelta(days=3, hours=5),
            'venue': 'Innovation Hub, Downtown Hall A, Hargeisa',
            'cap': 60,
            'status': EventStatus.OPEN,
            'cover': '/static/images/hub-hero.png',
        },
        {
            'title': 'Hands-on System Design & Architecture Lab',
            'desc': 'An interactive whiteboarding session breaking down real production architectures: database sharding, caching strategies with Redis, and resilient queue processing.',
            'cat': EventCategory.LAB,
            'start': now + timedelta(days=9, hours=4),
            'end': now + timedelta(days=9, hours=7),
            'venue': 'HTC Tech Space, Conference Room 2, Hargeisa',
            'cap': 35,
            'status': EventStatus.OPEN,
            'cover': '/static/images/speaker-hero.png',
        },
        {
            'title': 'Product Design Sprint: Building Fintech for the Horn',
            'desc': 'Collaborative workshop covering mobile-first design, accessibility in low-bandwidth regions, and intuitive payment flows for East African users.',
            'cat': EventCategory.WORKSHOP,
            'start': now + timedelta(days=16, hours=3),
            'end': now + timedelta(days=16, hours=6),
            'venue': 'Hargeisa Hub Co-working Stage',
            'cap': 40,
            'status': EventStatus.OPEN,
            'cover': '/static/images/hub-hero.png',
        },
        {
            'title': 'Fintech API Security & Penetration Testing',
            'desc': 'Completed meetup examining OWASP Top 10 API vulnerabilities, OAuth2 implementations, and token revocation patterns.',
            'cat': EventCategory.MEETUP,
            'start': now - timedelta(days=12, hours=3),
            'end': now - timedelta(days=12),
            'venue': 'Innovation Hub Hall A',
            'cap': 50,
            'status': EventStatus.COMPLETED,
            'cover': '/static/images/speaker-hero.png',
        }
    ]

    for ev in events_seed:
        e, _ = Event.objects.get_or_create(
            title=ev['title'],
            defaults={
                'description': ev['desc'],
                'category': ev['cat'],
                'start_datetime': ev['start'],
                'end_datetime': ev['end'],
                'venue': ev['venue'],
                'capacity': ev['cap'],
                'registration_deadline': ev['start'] - timedelta(hours=6),
                'status': ev['status'],
                'cover_image_url': ev['cover'],
                'created_by': admin_user
            }
        )

        # Add sample registrations
        if e.status == EventStatus.OPEN:
            EventRegistration.objects.get_or_create(
                event=e,
                attendee_email='guled.abdi@telesom.so',
                defaults={
                    'attendee_name': 'Guled Abdi',
                    'attendee_phone': '+252 63 4400112',
                    'status': 'REGISTERED',
                    'attendance_status': 'PENDING'
                }
            )
            EventRegistration.objects.get_or_create(
                event=e,
                attendee_email='nimco.farhan@designlab.so',
                defaults={
                    'attendee_name': 'Nimco Farhan',
                    'attendee_phone': '+252 63 4400223',
                    'status': 'REGISTERED',
                    'attendance_status': 'PENDING'
                }
            )
        elif e.status == EventStatus.COMPLETED:
            EventRegistration.objects.get_or_create(
                event=e,
                attendee_email='mohamed.khalif@builder.so',
                defaults={
                    'attendee_name': 'Mohamed Khalif',
                    'attendee_phone': '+252 63 4400334',
                    'status': 'REGISTERED',
                    'attendance_status': 'ATTENDED'
                }
            )
            EventRegistration.objects.get_or_create(
                event=e,
                attendee_email='hamse.abdirahman@cloudops.so',
                defaults={
                    'attendee_name': 'Hamse Abdirahman',
                    'attendee_phone': '+252 63 4400556',
                    'status': 'REGISTERED',
                    'attendance_status': 'ATTENDED'
                }
            )

    print("Created 4 sample events and participant registrations.")

    # 6. Create Meetings
    guled_prof = MemberProfile.objects.filter(user__email='guled.abdi@telesom.so').first()
    fathia_prof = MemberProfile.objects.filter(user__email='fathia.rashid@aihorn.so').first()

    meet1, _ = Meeting.objects.get_or_create(
        title="Senior Mentorship: Distributed Systems Architecture",
        defaults={
            'purpose': MeetingPurpose.MENTORSHIP,
            'start_datetime': now + timedelta(days=2, hours=3),
            'end_datetime': now + timedelta(days=2, hours=4),
            'venue': 'Innovation Hub, Mentor Office B',
            'meeting_link': 'https://meet.google.com/tc-hga-mentor',
            'status': MeetingStatus.CONFIRMED,
            'organizer_notes': '1-on-1 office hours focusing on PostgreSQL indexing and FastAPI deployment.',
            'created_by': admin_user
        }
    )
    if guled_prof and fathia_prof:
        MeetingParticipant.objects.get_or_create(
            meeting=meet1,
            member=guled_prof,
            defaults={'role_in_meeting': 'MENTOR', 'status': 'ACCEPTED'}
        )
        MeetingParticipant.objects.get_or_create(
            meeting=meet1,
            member=fathia_prof,
            defaults={'role_in_meeting': 'MENTEE', 'status': 'ACCEPTED'}
        )

    # 7. Create Announcements
    announcements_seed = [
        {
            'title': 'Applications for Cohort #3 are Now Open!',
            'content': 'We are officially welcoming applications for our Q2 2025 technology cohort. Share the join link with emerging software engineers, UI designers, and founders across Hargeisa and Somaliland.',
            'category': AnnouncementCategory.NEWS,
            'audience': AnnouncementAudience.ALL,
            'pinned': True,
        },
        {
            'title': 'Mentor Office Hours Schedule Announced',
            'content': 'Senior members and mentors will be holding 1-on-1 architecture review sessions every Thursday at the Innovation Hub. Check your member dashboard to view scheduled slots.',
            'category': AnnouncementCategory.MENTORSHIP,
            'audience': AnnouncementAudience.MEMBERS,
            'pinned': False,
        },
        {
            'title': 'Community Guidelines & Privacy Notice Updated',
            'content': 'To respect member privacy, personal contact coordinates (email & phone) remain hidden from public directory views by default. You can adjust visibility in your profile settings.',
            'category': AnnouncementCategory.NOTICE,
            'audience': AnnouncementAudience.MEMBERS,
            'pinned': False,
        }
    ]
    for an in announcements_seed:
        Announcement.objects.get_or_create(
            title=an['title'],
            defaults={
                'content': an['content'],
                'category': an['category'],
                'audience': an['audience'],
                'publication_status': PublicationStatus.PUBLISHED,
                'is_pinned': an['pinned'],
                'created_by': admin_user
            }
        )

    print("Created announcements and seed data completed successfully!")

if __name__ == '__main__':
    run_seed()
