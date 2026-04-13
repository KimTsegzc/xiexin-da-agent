import importlib
import unittest


_data_module = importlib.import_module("Backend.runtime.skills.skill_ccb_get_handler.data")
CCBHandlerTable = _data_module.CCBHandlerTable
HandlerChain = _data_module.HandlerChain
HandlerRecord = _data_module.HandlerRecord
_mask_person_name = _data_module._mask_person_name


class HandlerChainTests(unittest.TestCase):
    def test_mask_person_name_masks_all_but_first_character(self):
        self.assertEqual(_mask_person_name("靳x炳"), "靳xx")
        self.assertEqual(_mask_person_name("欧xx瑞"), "欧xxx")
        self.assertEqual(_mask_person_name("黄x"), "黄x")

    def test_render_uses_supervising_fallback_copy(self):
        chain = HandlerChain(
            department_head="黄xx（总经理）",
            supervising_head="",
            owner_name="黄x（消保岗）",
        )

        self.assertEqual(chain.render(), "黄xx（总经理）—分管通讯不确定—黄x（消保岗）")

    def test_render_skips_missing_department_head(self):
        chain = HandlerChain(
            department_head="",
            supervising_head="庄xx（副总经理）",
            owner_name="李xx（客户经营岗）",
        )

        self.assertEqual(chain.render(), "庄xx（副总经理）—李xx（客户经营岗）")

    def test_render_collapses_adjacent_duplicate_members(self):
        chain = HandlerChain(
            department_head="庄xx（副总经理）",
            supervising_head="庄xx（副总经理）",
            owner_name="李xx（客户经营岗）",
        )

        self.assertEqual(chain.render(), "庄xx（副总经理）—李xx（客户经营岗）")

    def test_resolve_chain_drops_duplicate_acting_head(self):
        acting_head = HandlerRecord(
            sequence="1",
            department="信用卡与消费金融业务部",
            role="副总经理",
            owner_name="庄x彬",
            office_phone="6600",
            responsibilities="主持部门全面工作；分管客户经营岗",
        )
        owner = HandlerRecord(
            sequence="2",
            department="信用卡与消费金融业务部",
            role="客户经营",
            owner_name="李x辉",
            office_phone="6607",
            responsibilities="负责广州地区信用卡业务营销方案的总体策划",
        )
        table = CCBHandlerTable(source_path=__file__, records=(acting_head, owner))

        chain = table.resolve_chain(owner)

        self.assertEqual(chain.department_head, "")
        self.assertEqual(chain.supervising_head, "庄xx（副总经理）")
        self.assertEqual(chain.render(), "庄xx（副总经理）—李xx（客户经营岗）")

    def test_render_lookup_context_masks_owner_names(self):
        head = HandlerRecord(
            sequence="1",
            department="信用卡与消费金融业务部",
            role="副总经理",
            owner_name="姚x彤",
            office_phone="6678",
            responsibilities="分管客户服务岗（消费者权益保护岗）",
        )
        owner = HandlerRecord(
            sequence="2",
            department="信用卡与消费金融业务部",
            role="客户服务岗（消费者权益保护岗）",
            owner_name="符x明",
            office_phone="6611",
            responsibilities="主管客服团队全面工作",
        )
        table = CCBHandlerTable(source_path=__file__, records=(head, owner))

        context = table.render_lookup_context()

        self.assertIn("负责人=姚xx", context)
        self.assertIn("负责人=符xx", context)

    def test_resolve_chain_drops_department_head_when_record_is_head(self):
        head = HandlerRecord(
            sequence="1",
            department="财务会计部",
            role="总经理",
            owner_name="卢xx",
            office_phone="6618",
            responsibilities="负责部门全面工作",
        )
        table = CCBHandlerTable(source_path=__file__, records=(head,))

        chain = table.resolve_chain(head)

        self.assertEqual(chain.department_head, "")
        self.assertEqual(chain.supervising_head, "")
        self.assertEqual(chain.render(), "分管通讯不确定—卢xx（总经理岗）")



if __name__ == "__main__":
    unittest.main()