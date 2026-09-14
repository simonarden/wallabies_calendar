import unittest
import update

class CalendarTests(unittest.TestCase):
    def test_window_changes_with_daylight_saving(self):
        self.assertEqual(update.utc_time('2026-09-19',12),'20260919T020000Z')
        self.assertEqual(update.utc_time('2026-10-17',12),'20261017T010000Z')
        self.assertEqual(update.utc_time('2026-10-17',18),'20261017T070000Z')
    def test_filtering_and_local_date(self):
        event=dict(id='Meeting_1',race_meet_id=1,name='Meeting',location_name='Caulfield',event_type='Racing',race_meet_type='Metro',event_start_time='2026-10-09T23:00:00Z')
        self.assertEqual(update.normalise(event)['date'],'2026-10-10')
        for venue in ['Sandown','Mornington','Sportsbet Sandown']:
            self.assertIsNone(update.normalise(dict(event,location_name=venue)))
        for kind in ['Trial','Jump Out']:
            self.assertIsNone(update.normalise(dict(event,race_meet_type=kind)))
        self.assertIsNone(update.normalise(dict(event,event_type='Events')))
        self.assertIsNotNone(update.normalise(dict(event,location_name='Caulfield Heath')))
    def test_rfc_folding_and_escaping(self):
        text='SUMMARY:'+update.escape('Café, '+('é'*100)+'; racing\\calendar')
        folded=update.fold(text)
        self.assertTrue(all(len(line.encode())<=75 for line in folded.split('\r\n')))
        self.assertEqual(folded.replace('\r\n ',''),text)

if __name__=='__main__': unittest.main()
