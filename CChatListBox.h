#pragma once
#include <afxwin.h>

class CChatListBox : public CListBox
{
public:
    CChatListBox();
    virtual ~CChatListBox();

    void AddColoredText(const CString& text, COLORREF color);

protected:
    afx_msg void DrawItem(LPDRAWITEMSTRUCT lpDrawItemStruct);
    afx_msg void MeasureItem(LPMEASUREITEMSTRUCT lpMeasureItemStruct);

    DECLARE_MESSAGE_MAP()
};