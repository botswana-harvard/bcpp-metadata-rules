from bcpp_community.surveys import BCPP_YEAR_3
from bcpp_labs.constants import MICROTUBE
from bcpp_status.status_db_helper import StatusDbHelper
from decimal import Decimal
from edc_constants.constants import POS, NEG, NO, YES, FEMALE, NAIVE, DEFAULTER, ON_ART
from edc_metadata_rules import PredicateCollection
from edc_registration.models import RegisteredSubject
from edc_reference import get_reference_name


class Predicates(PredicateCollection):

    app_label = 'bcpp_subject'
    visit_model = 'bcpp_subject.subjectvisit'
    status_helper_cls = StatusDbHelper

    def is_circumcised(self, visit):
        """Returns True if circumcised before or at visit
        report datetime.
        """
        return self.exists(
            reference_name=f'{self.app_label}.circumcision',
            subject_identifier=visit.subject_identifier,
            report_datetime__lte=visit.report_datetime,
            field_name='circumcised',
            value=YES)

    def is_hic_enrolled(self, visit):
        """Returns True if subject is enrolled to Hic.
        """
        return self.exists(
            reference_name=f'{self.app_label}.hicenrollment',
            subject_identifier=visit.subject_identifier,
            report_datetime__lte=visit.report_datetime,
            field_name='hic_permission',
            value=YES)

    def func_is_female(self, visit, **kwargs):
        registered_subject = RegisteredSubject.objects.get(
            subject_identifier=visit.subject_identifier)
        return registered_subject.gender == FEMALE

    def _has_last_year_partners(self, visit, partner_count=None):
        values = self.exists(
            reference_name=f'{self.app_label}.sexualbehaviour',
            subject_identifier=visit.subject_identifier,
            report_datetime=visit.report_datetime,
            field_name='last_year_partners')
        value = values[0] or 0
        try:
            value = int(value)
        except ValueError:
            value = int(Decimal(value))
        return value >= partner_count

    def func_requires_recent_partner(self, visit, **kwargs):
        return self._has_last_year_partners(visit, partner_count=1)

    def func_requires_second_partner_forms(self, visit, **kwargs):
        return self._has_last_year_partners(visit, partner_count=2)

    def func_requires_third_partner_forms(self, visit, **kwargs):
        return self._has_last_year_partners(visit, partner_count=3)

    def func_requires_venous(self, visit, **kwargs):
        reference_name = get_reference_name(
            f'{self.app_label}.subjectrequisition', MICROTUBE)
        panel_name = self.exists(
            reference_name=reference_name,
            subject_identifier=visit.subject_identifier,
            report_datetime=visit.report_datetime,
            field_name='panel_name',
            value=MICROTUBE)
        is_drawn = self.exists(
            reference_name=reference_name,
            subject_identifier=visit.subject_identifier,
            report_datetime=visit.report_datetime,
            field_name='is_drawn',
            value=NO)
        reason_not_drawn = self.exists(
            reference_name=reference_name,
            subject_identifier=visit.subject_identifier,
            report_datetime=visit.report_datetime,
            field_name='reason_not_drawn',
            value='collection_failed')
        return panel_name and is_drawn and reason_not_drawn

    def func_requires_hivuntested(self, visit, **kwargs):
        return self.exists(
            reference_name=f'{self.app_label}.hivtestinghistory',
            subject_identifier=visit.subject_identifier,
            report_datetime=visit.report_datetime,
            field_name='has_tested',
            value=NO)

    def func_requires_hivtestreview(self, visit, **kwargs):
        return self.exists(
            reference_name=f'{self.app_label}.hivtestinghistory',
            subject_identifier=visit.subject_identifier,
            report_datetime=visit.report_datetime,
            field_name='has_record',
            value=YES)

    def func_anonymous_member(self, visit, **kwargs):
        values = self.exists(
            reference_name=f'{self.app_label}.anonymousconsent',
            subject_identifier=visit.subject_identifier,
            field_name='consent_datetime')
        return [v for v in values if v is not None]

    def func_requires_hivlinkagetocare(self, visit, **kwargs):
        """Returns True if participant is a defaulter now or at baseline,
        is naive now or at baseline.
        """
        status_helper = self.status_helper_cls(visit=visit)
        if status_helper.defaulter_at_baseline:
            return True
        elif status_helper.naive_at_baseline:
            return True
        return False

    def func_art_defaulter(self, visit, **kwargs):
        """Returns True is a participant is a defaulter.
        """
        status_helper = self.status_helper_cls(visit=visit)
        return status_helper.final_arv_status == DEFAULTER

    def func_art_naive(self, visit, **kwargs):
        """Returns True if the participant art naive.
        """
        status_helper = self.status_helper_cls(visit=visit)
        return status_helper.final_arv_status == NAIVE

    def func_on_art(self, visit, **kwargs):
        """Returns True if the participant is on art.
        """
        return self.status_helper_cls(visit=visit).final_arv_status == ON_ART

    def func_requires_todays_hiv_result(self, visit, **kwargs):
        status_helper = self.status_helper_cls(visit=visit)
        return status_helper.final_hiv_status != POS

    def func_requires_pima_cd4(self, visit, **kwargs):
        """Returns True if subject is POS and ART naive.

        Note: if naive at baseline, is also required.
        """
        status_helper = self.status_helper_cls(visit=visit)
        return (status_helper.final_hiv_status == POS
                and (status_helper.final_arv_status == NAIVE
                     or status_helper.naive_at_baseline))

    def func_known_hiv_pos(self, visit, **kwargs):
        """Returns True if participant is NOT newly diagnosed POS.
        """
        status_helper = self.status_helper_cls(visit=visit)
        return status_helper.known_positive

    def func_requires_hic_enrollment(self, visit, **kwargs):
        """If the participant is tested HIV NEG and was not HIC
        enrolled then HIC is REQUIRED.

        Not required for last survey / bcpp-year-3.
        """
        if visit.survey_schedule == BCPP_YEAR_3:
            return False
        status_helper = self.status_helper_cls(visit=visit)
        return (status_helper.final_hiv_status == NEG
                and not self.is_hic_enrolled(visit))

    def func_requires_microtube(self, visit, **kwargs):
        """Returns True to trigger the Microtube requisition
        if not POS.
        """
        status_helper = self.status_helper_cls(visit=visit)
        return status_helper.final_hiv_status != POS

    def func_hiv_positive(self, visit, **kwargs):
        """Returns True if the participant is known or newly
        diagnosed HIV positive.
        """
        return self.status_helper_cls(visit=visit).final_hiv_status == POS

    def func_requires_circumcision(self, visit, **kwargs):
        """Return True if male is not reported as circumcised.
        """
        # TODO: we dont need to circumcise if POS??
        registered_subject = RegisteredSubject.objects.get(
            subject_identifier=visit.subject_identifier)
        if registered_subject.gender == FEMALE:
            return False
        return not self.is_circumcised(visit)

    def func_requires_rbd(self, visit, **kwargs):
        """Returns True if subject is POS.
        """
        if self.status_helper_cls(visit=visit).final_hiv_status == POS:
            return True
        return False

    def func_requires_vl(self, visit, **kwargs):
        """Returns True if subject is POS.
        """
        if self.status_helper_cls(visit=visit).final_hiv_status == POS:
            return True
        return False
