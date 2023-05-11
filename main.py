from praatio import textgrid
from os.path import join


class Sentence:
    def __init__(self, transcription, translation):
        self.transcription = transcription
        self.translation = translation


class ReferenceTrackingDevice:
    def __init__(self, form, referent, device, start, end, source_sentence):
        self.form = form
        self.referent = referent
        self.device = device
        self.start = start
        self.end = end
        self.source_sentence = source_sentence


class GridText:
    def __init__(self, filename, translation, cyrillic_transcription, latin_transcription,
                 annotation_form, annotation_indexation, annotation_device):
        self.filename = filename
        self.translation = translation
        self.cyrillic_transcription = cyrillic_transcription
        self.latin_transcription = latin_transcription
        self.annotation_form = annotation_form
        self.annotation_indexation = annotation_indexation
        self.annotation_device = annotation_device

    @classmethod
    def from_tg_file(cls, filepath, translation_name, cyrillic_transcription_name, latin_transcription_name,
                     annotation_form_name, annotation_indexation_name, annotation_device_name):
        tg = textgrid.openTextgrid(filepath, includeEmptyIntervals=True)

        translation, cyrillic_transcription, \
            latin_transcription, annotation_form, \
            annotation_indexation, annotation_device = \
            tg.tierDict[translation_name], \
                tg.tierDict[cyrillic_transcription_name], \
                tg.tierDict[latin_transcription_name], \
                tg.tierDict[annotation_form_name], \
                tg.tierDict[annotation_indexation_name], \
                tg.tierDict[annotation_device_name]

        return GridText(filepath, translation, cyrillic_transcription, latin_transcription,
                        annotation_form, annotation_indexation, annotation_device)

    @classmethod
    def get_labels(cls, layer):
        entries = layer.entryList
        labels = [label for _, _, label in entries]

        return labels

    def get_reference_tracking_devices(self):  # shitty code

        sentence_transcription_entries = self.latin_transcription.entryList
        sentence_translation_entries = self.translation.entryList
        annotation_form_entries = self.annotation_form.entryList
        annotation_indexation_entries = self.annotation_indexation.entryList
        annotation_device_entries = self.annotation_device.entryList
        sentence_id = 0

        devices = []

        if len(annotation_form_entries) != len(annotation_indexation_entries) != len(annotation_device_entries):
            raise IndexError("Annotation tiers differ in length!")

        if len(sentence_transcription_entries) != len(sentence_translation_entries):
            raise IndexError("Sentence tiers differ in length!")
        device_id = 0
        for start_device, end_device, label_device in annotation_form_entries:
            if annotation_indexation_entries[device_id][2] in ('pred', ''):
                device_id += 1
                continue
            while True:
                start_sentence, end_sentence, label_sentence = sentence_transcription_entries[sentence_id]
                _, _, label_sentence_translation = sentence_translation_entries[sentence_id]

                if (start_sentence <= start_device < end_sentence):
                    break

                sentence_id += 1

            if label_device not in label_sentence and label_device != 'Ø':
                print(label_device, ':', label_sentence)
                raise IndexError("Device is not found")

            reference_tracking_device = ReferenceTrackingDevice(label_device,
                                                                annotation_indexation_entries[device_id][2],
                                                                annotation_device_entries[device_id][2],
                                                                start_device,
                                                                end_device,
                                                                Sentence(label_sentence, label_sentence_translation))

            devices.append(reference_tracking_device)
            device_id += 1
        return devices

    def calculate_distance(self, reference_tracking_devices):
        for tracking_device_id, tracking_device in enumerate(reference_tracking_devices):
            if not tracking_device.startswith(('PROX', 'MED', 'DIST', 'SELF')):
                continue
            previous_referring_id = tracking_device_id - 1

            while previous_referring_id != -1:
                if tracking_device.referent == reference_tracking_devices[previous_referring_id].referent:
                    print(tracking_device.form, reference_tracking_devices[previous_referring_id].form)
                    break
                previous_referring_id -= 1


if __name__ == '__main__':
    path_to_test_tg = join('annotated_textgrids', 'kna_pears_alj_6.TextGrid')
    tier_names = ['translation', 'transcription_cyr', 'transcription_lat',
                 'annotation_form', 'annotation_indexation', 'annotation_device']

    test_tg = GridText.from_tg_file(path_to_test_tg, *tier_names)
    for device in test_tg.get_reference_tracking_devices():
        print(device.device, device.start, device.source_sentence.translation)

