from django.db import models
from django.conf import settings

class PartnershipInquiry(models.Model):
    organization_name = models.CharField(max_length=200, verbose_name="Organization Name")
    contact_name = models.CharField(max_length=150, verbose_name="Contact Person's Name")
    email = models.EmailField(verbose_name="Email Address")
    partnership_interests = models.CharField(max_length=400, blank=True, verbose_name="Partnership Interests")
    message = models.TextField(verbose_name="Message / Proposal")
    created_at = models.DateTimeField(auto_now_add=True)
    is_reviewed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Partnership Inquiry"
        verbose_name_plural = "Partnership Inquiries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.organization_name} - {self.contact_name} ({self.created_at.strftime('%Y-%m-%d')})"


DEFAULT_BIO = """Ahmed Liban Mohamed is a software engineering graduate from Abaarso Tech University in Somaliland and the founder of TechClub.

With a background in software development, teaching, and student leadership, Ahmed is passionate about using technology and collaboration to create opportunities for young people.

Through his experience in education and university leadership, he recognizes the importance of combining technical learning with meaningful professional relationships, knowledge sharing, and access to opportunities.

This belief inspired him to establish TechClub, a community designed to connect technology learners, developers, enthusiasts, and experienced professionals.

His vision is to help build a stronger, more connected technology ecosystem in Somaliland, where people can learn together, collaborate on projects, discover opportunities, and contribute to meaningful innovation."""

DEFAULT_STORY = """Across Hargeisa and Somaliland, young people are developing interests and skills in software engineering, web development, artificial intelligence, cybersecurity, design, and other technology fields.

However, opportunities for people learning and working in technology to find one another, exchange knowledge, build professional relationships, and collaborate across different learning environments can be limited.

A student learning web development may not know someone exploring artificial intelligence. A beginner may struggle to find guidance, while an experienced developer may want to share knowledge but lack opportunities to connect with aspiring learners.

I founded TechClub to help bridge this gap.

My goal is to create a community where technology learners and professionals can meet, share experiences, discover opportunities, learn from one another, and work together on meaningful projects.

TechClub is not intended to replace existing technology communities or organizations. Instead, it aims to complement the wider ecosystem by connecting people across backgrounds, institutions, skill levels, and professional networks.

I believe that when people share knowledge, support one another, and collaborate, individual talent can create greater collective impact."""

DEFAULT_MESSAGE = """I believe that talent becomes more powerful when people have the opportunity to connect, learn from one another, and work toward shared goals.

I started TechClub because I want young people in Hargeisa and Somaliland to have more opportunities to meet others who share their interests in technology, exchange knowledge, develop their skills, and turn their ideas into something meaningful.

My vision is to build a community that grows through collaboration, creates real opportunities, and contributes positively to our technology ecosystem.

We may begin with a small community, but through consistency, collaboration, and the support of people who share this vision, we can build something that lasts."""


class FounderProfile(models.Model):
    full_name = models.CharField(max_length=150, default="Ahmed Liban Mohamed", verbose_name="Founder Full Name")
    title = models.CharField(
        max_length=250, 
        default="Founder & Chairman of TechClub | Software Engineering Graduate",
        verbose_name="Professional Title"
    )
    headline = models.CharField(
        max_length=250, 
        default="Building Connections. Creating Opportunities.",
        verbose_name="Section Headline"
    )
    photo = models.ImageField(upload_to='founder/', blank=True, null=True, verbose_name="Portrait Photo Upload")
    photo_url = models.CharField(max_length=500, blank=True, default="/static/images/founder-ahmed.jpg", verbose_name="Fallback Image URL")
    
    education = models.CharField(
        max_length=250, 
        default="BSc in Software Engineering, Abaarso Tech University, Somaliland",
        verbose_name="Education Institution & Degree"
    )
    graduation_year = models.CharField(max_length=20, default="2026", verbose_name="Graduation Year")
    cgpa = models.CharField(max_length=20, default="3.97", verbose_name="CGPA")
    university_role = models.CharField(max_length=150, default="Founder & Chairman", verbose_name="University Role")
    linkedin_url = models.URLField(
        max_length=300, 
        default="https://www.linkedin.com/in/ahmed-iiban-mohamed-1448b6283/",
        verbose_name="LinkedIn Profile URL"
    )

    biography = models.TextField(default=DEFAULT_BIO, verbose_name="Founder Biography")
    central_message = models.CharField(
        max_length=300,
        default="The future of technology is stronger when the people behind it are connected.",
        verbose_name="Central Highlight Message"
    )
    story_subheading = models.CharField(
        max_length=250,
        default="Technology is more powerful when people connect.",
        verbose_name="Story Subheading"
    )
    story_body = models.TextField(default=DEFAULT_STORY, verbose_name="Founding Story")
    personal_message = models.TextField(default=DEFAULT_MESSAGE, verbose_name="Personal Statement")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Founder Profile & Settings"
        verbose_name_plural = "Founder Profile & Settings"

    def __str__(self):
        return f"Founder Profile: {self.full_name}"

    @property
    def display_photo(self):
        if self.photo and hasattr(self.photo, 'url'):
            return self.photo.url
        return self.photo_url or '/static/images/founder-ahmed.jpg'

    @classmethod
    def get_solo(cls):
        profile, created = cls.objects.get_or_create(id=1)
        return profile


class PartnerTier(models.TextChoices):
    STRATEGIC = 'STRATEGIC', 'Strategic Headline Partner'
    PREMIER = 'PREMIER', 'Premier Innovation Partner'
    ECOSYSTEM = 'ECOSYSTEM', 'Ecosystem & Growth Partner'
    COMMUNITY = 'COMMUNITY', 'Community & Venue Supporter'


class PartnerStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Review'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
    APPROVED = 'APPROVED', 'Approved & Published'
    REJECTED = 'REJECTED', 'Declined'


class CorporatePartner(models.Model):
    # Company Details
    company_name = models.CharField(max_length=200, verbose_name="Company / Organization Name")
    industry = models.CharField(max_length=100, default="Technology & Telecommunications", verbose_name="Industry Sector")
    website_url = models.URLField(verbose_name="Company Official Website")
    logo = models.ImageField(upload_to='partners/logos/', blank=True, null=True, verbose_name="Company Logo")
    logo_url = models.URLField(blank=True, null=True, verbose_name="Direct Logo Image URL (Alternative)")

    # Sponsorship Tier & Workflow Status
    tier = models.CharField(
        max_length=30,
        choices=PartnerTier.choices,
        default=PartnerTier.ECOSYSTEM,
        verbose_name="Partnership Tier"
    )
    status = models.CharField(
        max_length=30,
        choices=PartnerStatus.choices,
        default=PartnerStatus.PENDING,
        verbose_name="Review Status"
    )
    is_published = models.BooleanField(default=False, verbose_name="Publish on Website")
    is_featured_home = models.BooleanField(default=True, verbose_name="Feature on Homepage Trust Section")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Display Order (Ascending)")

    # Executive / Chairman Information (Trust Anchor)
    chairman_name = models.CharField(max_length=150, verbose_name="Chairman / Executive Full Name")
    chairman_title = models.CharField(max_length=150, verbose_name="Chairman / Executive Official Title")
    chairman_photo = models.ImageField(upload_to='partners/executives/', blank=True, null=True, verbose_name="Chairman / Executive Photo")
    chairman_photo_url = models.URLField(blank=True, null=True, verbose_name="Chairman Photo URL (Alternative)")
    chairman_quote = models.TextField(
        verbose_name="Executive Endorsement / Statement of Support",
        help_text="Direct quote from the chairman or CEO endorsing TechClub's role in advancing tech talent."
    )
    chairman_linkedin = models.URLField(blank=True, null=True, verbose_name="Chairman LinkedIn Profile")

    # Internal Representative / Contact Info
    contact_person_name = models.CharField(max_length=150, verbose_name="Contact Representative")
    contact_email = models.EmailField(verbose_name="Contact Work Email")
    contact_phone = models.CharField(max_length=40, verbose_name="Phone / WhatsApp Number")
    partnership_offering = models.TextField(
        blank=True,
        verbose_name="Partnership Support & Offering",
        help_text="e.g. Annual sponsorship budget, cloud compute credits, event hosting venue, hardware."
    )

    # Audit & Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_partners'
    )
    admin_notes = models.TextField(blank=True, verbose_name="Internal Organizer Notes")

    class Meta:
        verbose_name = "Corporate Partner"
        verbose_name_plural = "Corporate Partners"
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return f"{self.company_name} ({self.get_tier_display()}) - {self.get_status_display()}"

    @property
    def display_logo(self):
        if self.logo:
            try:
                return self.logo.url
            except Exception:
                pass
        return self.logo_url or ""

    @property
    def display_chairman_photo(self):
        if self.chairman_photo:
            try:
                return self.chairman_photo.url
            except Exception:
                pass
        return self.chairman_photo_url or ""

