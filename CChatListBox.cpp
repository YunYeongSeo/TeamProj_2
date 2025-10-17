#include "pch.h"
#include "CChatListBox.h"

BEGIN_MESSAGE_MAP(CChatListBox, CListBox)
END_MESSAGE_MAP()

CChatListBox::CChatListBox() {}
CChatListBox::~CChatListBox() {}

void CChatListBox::AddColoredText(const CString& text, COLORREF color)
{
    int index = AddString(text);
    SetItemData(index, (DWORD_PTR)color);
}

void CChatListBox::DrawItem(LPDRAWITEMSTRUCT lpDrawItemStruct)
{
    CDC dc;
    dc.Attach(lpDrawItemStruct->hDC);

    if (lpDrawItemStruct->itemID == -1)
    {
        dc.Detach();
        return;
    }

    COLORREF color = (COLORREF)GetItemData(lpDrawItemStruct->itemID);
    CString text;
    GetText(lpDrawItemStruct->itemID, text);

    dc.FillSolidRect(&lpDrawItemStruct->rcItem, RGB(255, 255, 255));
    dc.SetTextColor(color);
    dc.DrawText(text, &lpDrawItemStruct->rcItem, DT_LEFT | DT_SINGLELINE | DT_VCENTER);

    dc.Detach();
}

void CChatListBox::MeasureItem(LPMEASUREITEMSTRUCT lpMeasureItemStruct)
{
    lpMeasureItemStruct->itemHeight = 20; // 원하는 높이
}

