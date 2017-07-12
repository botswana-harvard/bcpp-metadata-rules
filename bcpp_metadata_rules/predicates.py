from django.core.exceptions import ObjectDoesNotExist

from edc_constants.constants import POS, NEG, NO, YES, FEMALE, NAIVE, DEFAULTER, ON_ART
from edc_metadata.rules import PredicateCollection
from edc_registration.models import RegisteredSubject

from bcpp_community.surveys import BCPP_YEAR_3
from bcpp_labs.constants import MICROTUBE
from bcpp_status.status_helper import StatusHelper


class Predicates(PredicateCollection):

    app_label = 'bcpp_subject'

    def is_circumcised(self, visit):
        """Returns True if circumcised before or at visit
        report datetime.
        """
        return self.exists_for_value(
            model='circumcision',
            identifier=visit.subject_identifier,
            report_datetime__lte=visit.report_datetime,
            field_name='circumcised',
            value=YES)

    def is_hic_enrolled(self, visit):
        """Returns True if subject is enrolled to Hic.
        """
        return self.exists(
            model='hicenrollment',
            identifier=visit.subject_identifier,
            report_datetime__lte=visit.report_datetime)

        model_cls = self.get_model('hicenrollment')
        try:
            model_cls.objects.get(
                subject_visit__subject_identifier=visit.subject_identifier,
                hic_permission=YES)
            return True
        except ObjectDoesNotExist:
            return False

    def func_is_female(self, visit, **kwargs):
        registered_subject = RegisteredSubject.objects.get(
            subject_identifier=visit.subject_identifier)
        return registered_subject.gender == FEMALE

    def func_requires_recent_partner(self, visit, **kwargs):
        model_cls = self.get_model('sexualbehaviour')
        sexual_behaviour = model_cls.objects.get(
            subject_visit=visit)
        if sexual_behaviour.last_year_partners:
            return True if int(sexual_behaviour.last_year_partners) >= 1 else False
        return False

    def func_requires_second_partner_forms(self, visit, **kwargs):
        model_cls = self.get_model('sexualbehaviour')
        sexual_behaviour = model_cls.objects.get(
            subject_visit=visit)
        if sexual_behaviour.last_year_partners:
            return True if int(sexual_behaviour.last_year_partners) >= 2 else False
        return False

    def func_requires_third_partner_forms(self, visit, **kwargs):
        model_cls = self.get_model('sexualbehaviour')
        sexual_behaviour = model_cls.objects.get(
            subject_visit=visit)
        if sexual_behaviour.last_year_partners:
            return True if int(sexual_behaviour.last_year_partners) >= 3 else False
        return False

    def func_requires_hivlinkagetocare(self, visit, **kwargs):
        """Returns True is a participant is a defaulter now or at baseline,
        is naive now or at baseline.
        """
        subject_helper = StatusHelper(subject_visit=visit)
        if subject_helper.defaulter_at_baseline:
            return True
        elif subject_helper.naive_at_baseline:
            return True
        return False

    def func_art_defaulter(self, visit, **kwargs):
        """Returns True is a participant is a defaulter.
        """
        subject_helper = StatusHelper(subject_visit=visit)
        return subject_helper.final_arv_status == DEFAULTER

    def func_art_naive(self, visit, **kwargs):
        """Returns True if the participant art naive.
        """
        subject_helper = StatusHelper(subject_visit=visit)
        return subject_helper.final_arv_status == NAIVE

    def func_on_art(self, visit, **kwargs):
        """Returns True if the participant is on art.
        """
        return StatusHelper(subject_visit=visit).final_arv_status == ON_ART

    def func_requires_todays_hiv_result(self, visit, **kwargs):
        subject_helper = StatusHelper(subject_visit=visit)
        return subject_helper.final_hiv_status != POS

    def func_requires_pima_cd4(self, visit, **kwargs):
        """Returns True if subject is POS and ART naive.

        Note: if naive at baseline, is also required.
        """
        subject_helper = StatusHelper(subject_visit=visit)
        return (subject_helper.final_hiv_status == POS
                and (subject_helper.final_arv_status == NAIVE
                     or subject_helper.naive_at_baseline))

    def func_known_hiv_pos(self, visit, **kwargs):
        """Returns True if participant is NOT newly diagnosed POS.
        """
        subject_helper = StatusHelper(subject_visit=visit)
        return subject_helper.known_positive

    def func_requires_hic_enrollment(self, visit, **kwargs):
        """If the participant is tested HIV NEG and was not HIC
        enrolled then HIC is REQUIRED.

        Not required for last survey / bcpp-year-3.
        """
        if visit.survey_schedule_object.name == BCPP_YEAR_3:
            return False
        subject_helper = StatusHelper(subject_visit=visit)
        return (subject_helper.final_hiv_status == NEG
                and not self.is_hic_enrolled(visit))

    def func_requires_microtube(self, visit, **kwargs):
        """Returns True to trigger the Microtube requisition if one is
        """
        # TODO: verify this
        model_cls = self.get_model('hivresult')
        subject_helper = StatusHelper(subject_visit=visit)
        try:
            hiv_result = model_cls.objects.get(subject_visit=visit)
        except model_cls.DoesNotExist:
            today_hiv_result = None
        else:
            today_hiv_result = hiv_result.hiv_result
        return (
            subject_helper.final_hiv_status != POS
            and not today_hiv_result)

    def func_hiv_positive(self, visit, **kwargs):
        """Returns True if the participant is known or newly
        diagnosed HIV positive.
        """
        return StatusHelper(subject_visit=visit).final_hiv_status == POS

    def func_requires_circumcision(self, visit, **kwargs):
        """Return True if male is not reported as circumcised.
        """
        if visit.household_member.gender == FEMALE:
            return False
        return not self.is_circumcised(visit)

    def func_requires_rbd(self, visit, **kwargs):
        """Returns True if subject is POS.
        """
        if StatusHelper(subject_visit=visit).final_hiv_status == POS:
            return True
        return False

    def func_requires_vl(self, visit, **kwargs):
        """Returns True if subject is POS.
        """
        if StatusHelper(subject_visit=visit).final_hiv_status == POS:
            return True
        return False

    def func_requires_venous(self, visit, **kwargs):
        model_cls = self.get_model('subjectrequisition')
        try:
            model_cls.objects.get(
                is_drawn=NO,
                panel_name=MICROTUBE,
                subject_visit=visit,
                reason_not_drawn='collection_failed')
        except model_cls.DoesNotExist:
            pass
        else:
            return True
        return False

    def func_requires_hivuntested(self, visit, **kwargs):
        """Only for ESS."""
        model_cls = self.get_model('hivtestinghistory')
        try:
            obj = model_cls.objects.get(
                subject_visit=visit)
        except model_cls.DoesNotExist:
            pass
        else:
            if obj and obj.has_tested == NO:
                return True
        return False

    def func_requires_hivtestreview(self, visit, **kwargs):
        """Only for ESS."""
        model_cls = self.get_model('hivtestinghistory')
        try:
            obj = model_cls.objects.get(
                subject_visit=visit)
        except model_cls.DoesNotExist:
            pass
        else:
            if obj and obj.has_record == YES:
                return True
        return False

    def func_anonymous_member(self, visit, **kwargs):
        model_cls = self.get_model('householdmember')
        try:
            household_member = model_cls.objects.get(
                subject_identifier=visit.subject_identifier)
            return household_member.anonymous
        except model_cls.DoesNotExist:
            return False
        except model_cls.MultipleObjectsReturned:
            return False
