import importlib
import unittest


_data_module = importlib.import_module("Backend.runtime.skills.skill_ccb_get_handler.data")
_skill_module = importlib.import_module("Backend.runtime.skills.skill_ccb_get_handler.skill")
CCBHandlerTable = _data_module.CCBHandlerTable
HandlerRecord = _data_module.HandlerRecord
_format_record_response = _skill_module._format_record_response


class CCBHandlerSkillResponseTests(unittest.TestCase):
    def test_leadership_record_adds_coordination_note(self):
        record = HandlerRecord(
            sequence="1",
            department="财务会计部",
            role="总经理",
            owner_name="卢x昆",
            office_phone="6618",
            responsibilities="负责部门全面工作",
        )
        table = CCBHandlerTable(source_path=__file__, records=(record,))

        response = _format_record_response(table, record, "财务会计部总经理负责部门全面工作")

        self.assertTrue(response.startswith("这个事比较综合，可能要找部门领导协调才行。\n"))
        self.assertIn("岗位：总经理岗", response)

    def test_non_leadership_record_omits_coordination_note(self):
        record = HandlerRecord(
            sequence="2",
            department="渠道与运营管理部",
            role="消保",
            owner_name="黄x",
            office_phone="6640",
            responsibilities="负责消费者权益保护工作",
        )
        table = CCBHandlerTable(source_path=__file__, records=(record,))

        response = _format_record_response(table, record, "职责覆盖消费者权益保护工作")

        self.assertFalse(response.startswith("这个事比较综合，可能要找部门领导协调才行。"))
        self.assertIn("岗位：消保岗", response)


if __name__ == "__main__":
    unittest.main()