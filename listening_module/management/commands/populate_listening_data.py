from collections import OrderedDict
import json
from django.core.management.base import BaseCommand
from listening_module.models import ListeningSentencesDataModel, ListeningStoryDataModel
from language_data.models import LanguageLevelModel, LanguageModel
from modules.models import TopicModel


class Command(BaseCommand):
    help = "Populate Listening Data for Greetings (Intermediate Level)"

    def handle(self, *args, **kwargs):
        sentences_data = {
  "story": [
    {
      "One sunny morning, Max walked into a café in Berlin and said": "English",
      "Guten Morgen": "German",
      "to the waiter. The waiter smiled and replied": "English",
      "Guten Morgen! Wie geht's?": "German",
      "which means 'Good Morning! How's it going?'.": "English"
    },
    {
      "Max, feeling adventurous, said": "English",
      "Mir geht es gut, danke!": "German",
      "which means 'I am doing well, thank you!'. Then he added": "English",
      "Und Ihnen?": "German",
      "which means 'And you?'.": "English"
    },
    {
      "The waiter chuckled and said": "English",
      "Auch gut, danke!": "German",
      "which means 'Also good, thank you!'. He then asked Max what he would like to order.": "English"
    },
    {
      "After ordering his coffee, Max noticed a dog wagging its tail. He turned to the owner and said": "English",
      "Schön, dich kennenzulernen": "German",
      "which means 'Nice to meet you'. The dog barked happily, and the owner laughed, replying": "English",
      "Freut mich, Sie kennenzulernen!": "German",
      "which means 'Nice to meet you too!'.": "English"
    },
    {
      "Later, as Max left the café, he waved to everyone and said": "English",
      "Auf Wiedersehen": "German",
      "to the waiter and": "English",
      "Tschüss": "German",
      "to the dog.": "English"
    },
    {
      "That evening, Max sat by the Brandenburg Gate and greeted a passerby with": "English",
      "Guten Abend": "German",
      "which means 'Good Evening'. The passerby smiled and replied": "English",
      "Guten Abend!": "German",
      "They had a pleasant chat about the city's beauty.": "English"
    },
    {
      "As the night fell, Max returned to his hotel and said to the receptionist": "English",
      "Gute Nacht": "German",
      "which means 'Good Night'. The receptionist responded warmly with": "English",
      "Gute Nacht! Schlaf gut!": "German",
      "which means 'Good Night! Sleep well!'.": "English"
    }
  ],
  "learning_sentences": [
    {
      "Greetings are an essential part of communication. In German, the word for 'hello' is": "English",
      "Hallo": "German",
      "which is used in informal settings. For formal occasions, Germans often say": "English",
      "Guten Tag": "German",
      "which translates to 'Good Day'.": "English"
    },
    {
      "In the morning, you can greet someone with": "English",
      "Guten Morgen": "German",
      "meaning 'Good Morning'.": "English",
      "In the evening, Germans say": "English",
      "Guten Abend": "German",
      "which means 'Good Evening'.": "English"
    },
    {
      "When leaving, you can use the phrase": "English",
      "Tschüss": "German",
      "which is equivalent to 'Bye'.": "English",
      "Alternatively, in informal settings, you might hear": "English",
      "Auf Wiedersehen": "German",
      "to say 'Goodbye' formally.": "English"
    },
    {
      "A common way to ask 'How are you?' in German is": "English",
      "Wie geht es Ihnen?": "German",
      "This is a formal way to inquire about someone's well-being.": "English",
      "For informal situations, you can simply say": "English",
      "Wie geht's?": "German",
      "which means 'How's it going?'.": "English"
    },
    {
      "When someone asks you how you are, you might reply with": "English",
      "Mir geht es gut": "German",
      "which means 'I am doing well'.": "English",
      "If you're not doing well, you could say": "English",
      "Mir geht es nicht so gut": "German",
      "meaning 'I am not doing so well'.": "English"
    },
    {
      "To express gratitude, Germans say": "English",
      "Danke": "German",
      "which means 'Thank you'.": "English",
      "You might also say": "English",
      "Vielen Dank": "German",
      "to mean 'Many thanks'.": "English"
    },
    {
      "To respond to 'Thank you', you can say": "English",
      "Bitte": "German",
      "which means 'You're welcome'.": "English"
    },
    {
      "When meeting someone for the first time, you might say": "English",
      "Schön, dich kennenzulernen": "German",
      "which means 'Nice to meet you'.": "English",
      "For informal settings, you could say": "English",
      "Freut mich, Sie kennenzulernen": "German",
      "which also translates to 'Nice to meet you'.": "English"
    },
    {
      "Finally, a friendly way to wish someone a good day is to say": "English",
      "Schönen Tag noch!": "German",
      "which means 'Have a nice day!'.": "English",
      "And in the evening, you might say": "English",
      "Gute Nacht": "German",
      "to wish them 'Good Night'.": "English"
    }
  ]
}


        # Fetch related records
        topic = TopicModel.objects.get(name="Greetings",level__name='Beginner')
        base_language = LanguageModel.objects.get(name="English")
        learning_language = LanguageModel.objects.get(name="German")
        new_listening_sentence_data_id = 0
        # Add sentences to ListeningSentencesDataModel
        for sentence_dict in sentences_data['learning_sentences']:
            new_data = ListeningSentencesDataModel.objects.create(
                topic=topic,
                base_language=base_language,
                learning_language=learning_language,
                sentence=str(sentence_dict),  # Save the dictionary as JSON
                is_active=True,
                is_deleted=False
            )
            new_listening_sentence_data_id = new_data.id

        # Add story to ListeningStoryDataModel
        '''story = sentences_data['story']  # Save the entire story as a JSON list
        ListeningStoryDataModel.objects.create(
            listening_sentence_data=ListeningSentencesDataModel(id=new_listening_sentence_data_id),
            story=story,
            is_active=True,
            is_deleted=False
        )'''

        self.stdout.write("Data has been added successfully!")
