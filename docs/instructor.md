## WELCOME to ACCORNS

ACCORNS or Admin Control Center Overseeing RAG Needed for SCUIRREL is the
instructor-facing backend application to SCUIRREL. Here you can set-up, manage and
monitor SCUIRREL and the students' interactions with it.

_If you are looking for more details on how to analyse the data collected by SCUIRREL or
ACCORNS, please read the [researcher guide](researcher.md)_

## Uploading relevant course materials

Instructors can upload text-based materials relevant to the topics students should
discuss with SCUIRREL. During the conversation, SCUIRREL will refer to these materials
using retrieval augmented generation (RAG) to provide improve the quality an accuracy of
the conversation. You need to have uploaded at least one document before you can start
configuring topics and concepts. The application should accept most text based file
formats (e.g. .txt, .pdf, .docx, .md) and even powerpoint slides (not extensively
tested).

_NOTE: The uploaded material will be sent to the LLM (e.g. ChatGPT), so please ensure
that you have the necessary permissions to share this content and read the privacy
policies to know what is being done with your data on their side._

## Creating topics and concepts

Each **topic** you create will be a choice for students to discuss with SCUIRREL. You
can compare a topic to a textbook chapter. The scope should be something that can be
revisited in a short conversation.

- You can add, edit or archive topics as needed
- We recommend to only edit a topic in case of typos or small changes that do not
  significantly change the covered content (create new one otherwise)
- Make sure to upload relevant course materials before creating new topics as this will
  improve the quality of the conversation SCUIRREL has

For each topic, you have to create one or more **concepts**. A concept can be seen as a
topic-related fact or piece of information that you want SCUIRREL to check with your
students. Compare this to bullet point summarising the textbook chapter.

- You can add, edit or archive concepts as needed
- Early experiment suggest that about 5-10 concepts per topic is a good number to keep
  the conversation engaging but not too long, but feel free to experiment with this and
  provide us with feedback
- There is currently no option yet to reorder the concepts (SCUIRREL goes through them
  in order), but this should be part of a future releaseF

The way SCUIRREL works is that it will use the topic as the main conversation thread,
and systematically check each of the concepts (in order) with the student by walking
through the list you created. Whilst this is happening, a second LLM will monitor the
conversation and decide if a student demonstrates enough understanding of a concept to
move on to the next one. Once all concepts belonging to a topic have been covered,
SCUIRREL will end the conversation.

## Generating quiz questions

For each topic, you can also create quiz questions students can take to verify their
understanding. in this case, the LLM will help generate these questions based on the
concepts you provided for a topic and the uploaded materials. These are the steps to
follow:

- Go to the quiz question tab, select a topic, and click the generate quiz question
  button
- The LLM will try and generate a question, 4 possible answers and an explanation why
  each answer is correct or incorrect
- It is possible the LLM fails at this task in which case you might see an error message
- Once generated, you will have the option to review everything and edit any part of the
  question, answer or explanation to ensure it is correct and good for assessment.
- Questions can be archived at any time, in which case they will no longer be shows to
  students

_Given this is a more summative type of assessment we opted to have the instructor
validate each question instead of having the LLM directly generate them for the student.
This is also useful from a monitoring / research perspective to compare the conversation
with SCUIRREL to the performance on the quiz questions. For more info, we refer to the
[researcher documentation](researcher.md)_

_This project was designed to help student gauge their background on this topic before
they come into class, or revisit it after class. For this reason, we do not recommend
using this application to teach brand new material, but rather serve as an aid for
students._
