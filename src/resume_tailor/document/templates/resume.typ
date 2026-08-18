// ATS-friendly single-column resume template.
// Consumes resume_data.json, placed alongside this file at compile time.
#let data = json("resume_data.json")

#set page(margin: (x: 0.65in, y: 0.55in))
#set text(font: "Liberation Sans", size: 10pt, lang: "en")
#set par(leading: 0.55em, justify: false)

#let section(title) = {
  v(0.6em)
  text(size: 12pt, weight: "bold")[#upper(title)]
  v(-0.3em)
  line(length: 100%, stroke: 0.5pt)
  v(0.2em)
}

#let date_range(start, end) = {
  if start == none and end == none {
    none
  } else {
    let s = if start == none { "" } else { start }
    let e = if end == none { "Present" } else { end }
    s + " - " + e
  }
}

#align(center)[
  #text(size: 18pt, weight: "bold")[#data.full_name]
]
#if data.contact_summary != none [
  #align(center)[#text(size: 9pt)[#data.contact_summary]]
]

#if data.summary != none [
  #section("Summary")
  #data.summary
]

#if data.experience.len() > 0 [
  #section("Experience")
  #for exp in data.experience [
    #block(above: 0.5em, below: 0.2em)[
      #text(weight: "bold")[#exp.title] --- #emph[#exp.company]
      #let dr = date_range(exp.start_date, exp.end_date)
      #if dr != none [ #h(1fr) #dr ]
    ]
    #for bullet in exp.bullets [
      - #bullet
    ]
  ]
]

#if data.education.len() > 0 [
  #section("Education")
  #for edu in data.education [
    #let degree_line = if edu.field_of_study != none {
      edu.degree + ", " + edu.field_of_study
    } else {
      edu.degree
    }
    #block(above: 0.4em, below: 0.2em)[
      #text(weight: "bold")[#degree_line] --- #edu.institution
      #if edu.graduation_date != none [ #h(1fr) #edu.graduation_date ]
    ]
  ]
]

#if data.hard_skills.len() > 0 or data.soft_skills.len() > 0 [
  #section("Skills")
  #(data.hard_skills + data.soft_skills).join(", ")
]

#if data.projects.len() > 0 [
  #section("Projects")
  #for proj in data.projects [
    #block(above: 0.4em, below: 0.2em)[
      #text(weight: "bold")[#proj.name]
    ]
    #for bullet in proj.bullets [
      - #bullet
    ]
  ]
]
